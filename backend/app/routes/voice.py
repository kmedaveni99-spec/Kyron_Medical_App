"""Voice routes - handles voice call initiation and Twilio webhooks."""
from fastapi import APIRouter, Depends, Form, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Conversation, Message
from app.schemas import VoiceCallRequest
from app.services.voice_service import initiate_voice_call, generate_greeting_twiml, generate_response_twiml
from app.services.ai_engine import get_ai_response
from app.routes.chat import session_contexts

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


@router.post("/initiate")
async def initiate_call(request: VoiceCallRequest, db: AsyncSession = Depends(get_db)):
    """Initiate a voice call to the patient to continue the chat."""
    result = await initiate_voice_call(request.phone_number, request.session_id)
    return result


@router.post("/webhook")
async def voice_webhook(
    session_id: str = Query(""),
    db: AsyncSession = Depends(get_db)
):
    """Twilio webhook - initial call handler, generates greeting TwiML."""
    summary = await get_conversation_summary(session_id, db)
    twiml = generate_greeting_twiml(session_id, summary)
    return Response(content=twiml, media_type="application/xml")


@router.post("/respond")
async def voice_respond(
    session_id: str = Query(""),
    SpeechResult: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """Twilio webhook - processes speech input and generates AI response."""
    user_speech = SpeechResult.strip()

    if not user_speech:
        twiml = generate_response_twiml(
            "I didn't catch that. Could you please repeat?",
            session_id
        )
        return Response(content=twiml, media_type="application/xml")

    # Get conversation history
    result = await db.execute(
        select(Conversation).where(Conversation.session_id == session_id)
    )
    conversation = result.scalars().first()

    history = []
    if conversation:
        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
        )
        messages = msg_result.scalars().all()
        history = [{"role": m.role, "content": m.content} for m in messages]

        # Save the voice user message
        voice_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=f"[Voice] {user_speech}"
        )
        db.add(voice_msg)
        await db.commit()

    # Add current voice message to history
    history.append({"role": "user", "content": user_speech})

    # Get AI response
    ctx = session_contexts.get(session_id, {})
    reply, tool_calls = await get_ai_response(history, ctx, session_id=session_id)

    # For voice, we skip complex tool calls and just give a conversational response
    # (booking via voice would need more sophisticated handling)
    if not reply:
        reply = "I understand. Is there anything else I can help you with?"

    # Save assistant reply
    if conversation:
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=f"[Voice] {reply}"
        )
        db.add(assistant_msg)
        await db.commit()

    twiml = generate_response_twiml(reply, session_id)
    return Response(content=twiml, media_type="application/xml")


@router.post("/status")
async def voice_status():
    """Twilio call status webhook."""
    return {"status": "received"}

