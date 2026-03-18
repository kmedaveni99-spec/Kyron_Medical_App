"""Voice routes - handles voice call initiation and Twilio webhooks."""
import datetime
import re
from fastapi import APIRouter, Depends, Form, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models import Conversation, Message, Patient
from app.schemas import VoiceCallRequest
from app.services.voice_service import initiate_voice_call, generate_greeting_twiml, generate_response_twiml
from app.services.ai_engine import get_ai_response, get_ai_response_with_tool_results
from app.routes.chat import session_contexts, execute_tool_call, get_or_create_conversation, sanitize_customer_reply

router = APIRouter()


async def get_conversation_summary(session_id: str, db: AsyncSession) -> str:
    """Get a brief summary of the chat conversation for voice handoff."""
    result = await db.execute(
        select(Conversation).where(Conversation.session_id == session_id)
    )
    conversation = result.scalars().first()
    if not conversation:
        return ""

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(5)
    )
    messages = msg_result.scalars().all()

    if not messages:
        return ""

    # Get last few messages as context summary
    summary_parts = []
    for msg in reversed(messages):
        if msg.role in ("user", "assistant"):
            summary_parts.append(f"{msg.role}: {msg.content[:100]}")

    return " | ".join(summary_parts[-3:])


def _normalize_phone_for_lookup(phone: str) -> str:
    """Normalize phone string to last 10 digits for tolerant matching."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) >= 10:
        return digits[-10:]
    return digits


async def resolve_session_id(session_id: str, from_number: str, db: AsyncSession) -> str:
    """Resolve session id from query or infer from known patient phone for inbound callbacks."""
    if session_id:
        return session_id

    normalized = _normalize_phone_for_lookup(from_number)
    if not normalized:
        return f"voice_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    result = await db.execute(
        select(Conversation.session_id, Patient.phone)
        .join(Patient, Patient.id == Conversation.patient_id)
        .order_by(desc(Conversation.updated_at))
    )
    for candidate_session_id, phone in result.all():
        if _normalize_phone_for_lookup(phone) == normalized:
            return candidate_session_id

    return f"voice_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"


@router.post("/initiate")
async def initiate_call(request: VoiceCallRequest, db: AsyncSession = Depends(get_db)):
    """Initiate a voice call to the patient to continue the chat."""
    result = await initiate_voice_call(request.phone_number, request.session_id)
    return result


@router.post("/webhook")
async def voice_webhook(
    session_id: str = Query(""),
    From: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """Twilio webhook - initial call handler, generates greeting TwiML."""
    resolved_session_id = await resolve_session_id(session_id, From, db)
    summary = await get_conversation_summary(resolved_session_id, db)
    twiml = generate_greeting_twiml(resolved_session_id, summary)
    return Response(content=twiml, media_type="application/xml")


@router.post("/respond")
async def voice_respond(
    session_id: str = Query(""),
    From: str = Form(""),
    SpeechResult: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """Twilio webhook - processes speech input and generates AI response."""
    resolved_session_id = await resolve_session_id(session_id, From, db)
    user_speech = SpeechResult.strip()

    if not user_speech:
        twiml = generate_response_twiml(
            "I didn't catch that. Could you please repeat?",
            resolved_session_id
        )
        return Response(content=twiml, media_type="application/xml")

    # Get or create conversation for this voice session.
    conversation = await get_or_create_conversation(resolved_session_id, db)

    history = []
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()
    history = [{"role": m.role, "content": m.content} for m in messages]

    # Save the voice user message.
    voice_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=f"[Voice] {user_speech}"
    )
    db.add(voice_msg)
    await db.commit()

    # Add current voice message to history
    history.append({"role": "user", "content": user_speech})

    # Get AI response (voice now supports tool workflows for scheduling/refill/office flows).
    ctx = session_contexts.get(resolved_session_id, {})
    reply, tool_calls = await get_ai_response(history, ctx, session_id=resolved_session_id)

    max_iterations = 5
    iteration = 0
    while tool_calls and iteration < max_iterations:
        iteration += 1
        tool_results = []
        for tc in tool_calls:
            result = await execute_tool_call(tc["name"], tc["arguments"], resolved_session_id, db)
            tool_results.append({
                "tool_call_id": tc["id"],
                "result": result,
            })

        reply, tool_calls = await get_ai_response_with_tool_results(
            history,
            tool_results,
            tool_calls,
            session_contexts.get(resolved_session_id, {}),
            session_id=resolved_session_id,
        )

    if not reply:
        reply = "I understand. Is there anything else I can help you with?"

    reply = sanitize_customer_reply(reply)

    # Save assistant reply
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=f"[Voice] {reply}"
    )
    db.add(assistant_msg)
    await db.commit()

    twiml = generate_response_twiml(reply, resolved_session_id)
    return Response(content=twiml, media_type="application/xml")


@router.post("/status")
async def voice_status():
    """Twilio call status webhook."""
    return {"status": "received"}

