"""Chat route - main conversational endpoint."""
import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Conversation, Message, Patient
from app.schemas import ChatRequest, ChatResponse, PatientIntake
from app.services.ai_engine import get_ai_response, get_ai_response_with_tool_results
from app.services.doctor_matcher import match_doctor
from app.services.scheduling import get_available_slots, book_appointment
from app.services.email_service import send_appointment_confirmation
from app.services.sms_service import send_appointment_sms
from app.services.ai_engine import sync_mock_intake_state

router = APIRouter()

# In-memory session context store (in production, use Redis)
session_contexts: dict[str, dict] = {}

OFFICE_INFO = {
    "name": "Kyron Medical Practice",
    "address": "450 Medical Center Drive, Suite 200, San Francisco, CA 94102",
    "phone": "(415) 555-0100",
    "fax": "(415) 555-0101",
    "email": "info@kyronmedical.com",
    "website": "www.kyronmedical.com",
    "hours": {
        "Monday": "8:00 AM - 5:00 PM",
        "Tuesday": "8:00 AM - 5:00 PM",
        "Wednesday": "8:00 AM - 5:00 PM",
        "Thursday": "8:00 AM - 5:00 PM",
        "Friday": "8:00 AM - 5:00 PM",
        "Saturday": "9:00 AM - 1:00 PM",
        "Sunday": "Closed"
    },
    "providers": [
        {"name": "Dr. Maria Rivera", "specialty": "Orthopedics"},
        {"name": "Dr. Raj Patel", "specialty": "Cardiology"},
        {"name": "Dr. Sarah Kim", "specialty": "Dermatology"},
        {"name": "Dr. Chidi Okafor", "specialty": "Neurology"},
        {"name": "Dr. Emily Chen", "specialty": "Gastroenterology"}
    ]
}

# Simulated prescription data
RX_DATABASE = {
    "lisinopril": {"status": "Ready for pickup", "pharmacy": "CVS Pharmacy - Market St", "refills_remaining": 3, "last_filled": "March 5, 2026"},
    "metformin": {"status": "Processing", "pharmacy": "Walgreens - Mission St", "refills_remaining": 2, "last_filled": "February 28, 2026", "estimated_ready": "Tomorrow by 2:00 PM"},
    "atorvastatin": {"status": "Requires doctor approval", "pharmacy": "CVS Pharmacy - Market St", "refills_remaining": 0, "last_filled": "January 15, 2026", "note": "Your doctor needs to authorize a new prescription. We'll contact you once approved."},
    "omeprazole": {"status": "Ready for pickup", "pharmacy": "Walgreens - Mission St", "refills_remaining": 5, "last_filled": "March 10, 2026"},
    "sertraline": {"status": "Shipped - arriving March 19", "pharmacy": "Mail Order Pharmacy", "refills_remaining": 4, "last_filled": "February 20, 2026"},
}


async def get_or_create_conversation(session_id: str, db: AsyncSession) -> Conversation:
    """Get existing conversation or create a new one."""
    result = await db.execute(
        select(Conversation).where(Conversation.session_id == session_id)
    )
    conversation = result.scalars().first()

    if not conversation:
        conversation = Conversation(session_id=session_id)
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    return conversation


async def get_conversation_history(conversation_id: int, db: AsyncSession) -> list[dict]:
    """Get message history for a conversation."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    history = []
    for msg in messages:
        history.append({"role": msg.role, "content": msg.content})

    return history


async def save_message(conversation_id: int, role: str, content: str, db: AsyncSession):
    """Save a message to the conversation."""
    msg = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(msg)
    await db.commit()


async def execute_tool_call(
    tool_name: str,
    arguments: dict,
    session_id: str,
    db: AsyncSession
) -> dict:
    """Execute a tool call and return the result."""
    ctx = session_contexts.get(session_id, {})

    if tool_name == "collect_patient_intake":
        # Validate required fields before creating patient
        first_name = (arguments.get("first_name") or "").strip()
        last_name = (arguments.get("last_name") or "").strip()
        phone = (arguments.get("phone") or "").strip()
        email = (arguments.get("email") or "").strip()
        dob_str = (arguments.get("date_of_birth") or "").strip()

        missing = []
        if not first_name or first_name.lower() in ("unknown", "patient", "n/a", ""):
            missing.append("first name")
        if not last_name or last_name.lower() in ("unknown", "user", "n/a", ""):
            missing.append("last name")
        if not phone or len(phone) < 7:
            missing.append("phone number")
        if not email or "@" not in email:
            missing.append("email address")
        if not dob_str or dob_str in ("1990-01-01", ""):
            missing.append("date of birth")

        if missing:
            return {
                "success": False,
                "missing_fields": missing,
                "message": f"I still need the patient's {', '.join(missing)} before I can register them. Please ask the patient for this information."
            }

        # Create patient record
        try:
            dob = datetime.date.fromisoformat(dob_str)
        except (ValueError, KeyError):
            dob = datetime.date(1990, 1, 1)

        patient = Patient(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=dob,
            phone=phone,
            email=email,
            sms_opt_in=arguments.get("sms_opt_in", False)
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)

        # Link patient to conversation
        result = await db.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        conv = result.scalars().first()
        if conv:
            conv.patient_id = patient.id
            await db.commit()

        # Update session context
        ctx["patient"] = {
            "id": patient.id,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "phone": patient.phone,
            "email": patient.email,
            "sms_opt_in": patient.sms_opt_in
        }
        session_contexts[session_id] = ctx

        return {
            "success": True,
            "patient_id": patient.id,
            "message": f"Patient {patient.first_name} {patient.last_name} registered successfully."
        }

    elif tool_name == "match_doctor_specialty":
        reason = arguments["reason"]
        doctor_data = await match_doctor(reason, db)

        if doctor_data:
            ctx["matched_doctor"] = doctor_data
            session_contexts[session_id] = ctx
            return {
                "success": True,
                "doctor": doctor_data,
                "message": f"Matched to {doctor_data['name']} ({doctor_data['specialty']}). {doctor_data['bio']}"
            }
        else:
            return {
                "success": False,
                "message": "Unfortunately, our practice doesn't have a specialist for that specific concern. Our specialties include Orthopedics, Cardiology, Dermatology, Neurology, and Gastroenterology. You may want to consult your primary care physician for a referral."
            }

    elif tool_name == "get_available_slots":
        doctor_id = arguments["doctor_id"]
        preferred_day = arguments.get("preferred_day")
        preferred_time = arguments.get("preferred_time")

        slots = await get_available_slots(doctor_id, db, preferred_day, preferred_time)

        if slots:
            ctx["available_slots"] = slots
            session_contexts[session_id] = ctx
            return {
                "success": True,
                "slots": slots,
                "count": len(slots),
                "message": f"Found {len(slots)} available slots."
            }
        else:
            return {
                "success": False,
                "message": "No available slots found for the specified criteria. Would you like to try a different day or time?"
            }

    elif tool_name == "book_appointment":
        patient_data = ctx.get("patient")
        if not patient_data:
            return {"success": False, "message": "Patient information not collected yet."}

        result = await book_appointment(
            patient_id=patient_data["id"],
            slot_id=arguments["slot_id"],
            reason=arguments["reason"],
            db=db
        )

        if result:
            ctx["appointment"] = result
            session_contexts[session_id] = ctx

            # Send email confirmation (async, non-blocking)
            try:
                await send_appointment_confirmation(result)
            except Exception as e:
                print(f"Email notification error: {e}")

            # Send SMS if opted in
            try:
                await send_appointment_sms(result)
            except Exception as e:
                print(f"SMS notification error: {e}")

            return {
                "success": True,
                "appointment": result,
                "message": f"Appointment booked with {result['doctor_name']} on {result['date_time']}. Confirmation has been sent to {result['patient_email']}."
            }
        else:
            return {"success": False, "message": "That slot is no longer available. Please choose another time."}

    elif tool_name == "check_rx_status":
        med_name = arguments.get("medication_name", "").lower().strip()
        # Fuzzy match
        matched_rx = None
        for rx_name, rx_data in RX_DATABASE.items():
            if rx_name in med_name or med_name in rx_name:
                matched_rx = {"medication": rx_name.title(), **rx_data}
                break

        if matched_rx:
            return {"success": True, "prescription": matched_rx}
        else:
            return {
                "success": False,
                "message": f"I couldn't find a prescription for '{arguments.get('medication_name', '')}' in our system. Please check the medication name or contact our pharmacy directly at (415) 555-0100."
            }

    elif tool_name == "get_office_info":
        return {"success": True, "office": OFFICE_INFO}

    return {"success": False, "message": "Unknown tool."}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Main chat endpoint - processes user messages and returns AI responses."""
    session_id = request.session_id
    user_message = request.message.strip()

    if not user_message:
        return ChatResponse(reply="Please type a message to get started!")

    # Get or create conversation
    conversation = await get_or_create_conversation(session_id, db)

    # Load conversation history
    history = await get_conversation_history(conversation.id, db)

    # Save user message
    await save_message(conversation.id, "user", user_message, db)
    history.append({"role": "user", "content": user_message})

    # Get session context
    ctx = session_contexts.get(session_id, {})

    # Get AI response
    reply, tool_calls = await get_ai_response(history, ctx, session_id=session_id)

    # Process tool calls iteratively
    max_iterations = 5
    iteration = 0
    action = None
    action_data = None

    while tool_calls and iteration < max_iterations:
        iteration += 1
        tool_results = []

        for tc in tool_calls:
            result = await execute_tool_call(tc["name"], tc["arguments"], session_id, db)
            tool_results.append({
                "tool_call_id": tc["id"],
                "result": result
            })

            # Determine UI actions to send to frontend
            if tc["name"] == "collect_patient_intake" and result.get("success"):
                action = "patient_registered"
                action_data = {"patient_id": result["patient_id"]}
            elif tc["name"] == "collect_patient_intake" and not result.get("success"):
                if result.get("missing_fields"):
                    action = "show_intake_form"
                    action_data = {"missing_fields": result.get("missing_fields", [])}
            elif tc["name"] == "get_available_slots" and result.get("success"):
                action = "show_slots"
                action_data = {"slots": result["slots"]}
            elif tc["name"] == "book_appointment" and result.get("success"):
                action = "appointment_booked"
                action_data = result["appointment"]
            elif tc["name"] == "get_office_info" and result.get("success"):
                action = "show_office_info"
                action_data = result["office"]
            elif tc["name"] == "check_rx_status":
                action = "show_rx_status"
                action_data = result.get("prescription", {"message": result.get("message", "")})

        # Continue conversation with tool results
        reply, tool_calls = await get_ai_response_with_tool_results(
            history, tool_results, tool_calls, session_contexts.get(session_id, {}), session_id=session_id
        )

    # Save assistant reply
    if reply:
        await save_message(conversation.id, "assistant", reply, db)

    return ChatResponse(reply=reply, action=action, data=action_data)


@router.post("/intake")
async def submit_intake(intake: PatientIntake, db: AsyncSession = Depends(get_db)):
    """Direct intake submission from the frontend form."""
    try:
        dob = datetime.date.fromisoformat(intake.date_of_birth)
    except ValueError:
        dob = datetime.date(1990, 1, 1)

    patient = Patient(
        first_name=intake.first_name,
        last_name=intake.last_name,
        date_of_birth=dob,
        phone=intake.phone,
        email=intake.email,
        sms_opt_in=intake.sms_opt_in
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)

    if intake.session_id:
        conv_result = await db.execute(
            select(Conversation).where(Conversation.session_id == intake.session_id)
        )
        conversation = conv_result.scalars().first()
        if conversation:
            conversation.patient_id = patient.id
            await db.commit()

        session_contexts[intake.session_id] = {
            **session_contexts.get(intake.session_id, {}),
            "patient": {
                "id": patient.id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "phone": patient.phone,
                "email": patient.email,
                "sms_opt_in": patient.sms_opt_in,
            }
        }

        sync_mock_intake_state(
            intake.session_id,
            {
                "first_name": intake.first_name,
                "last_name": intake.last_name,
                "date_of_birth": intake.date_of_birth,
                "phone": intake.phone,
                "email": intake.email,
                "reason": intake.reason,
            }
        )

    return {
        "success": True,
        "patient_id": patient.id,
        "patient_phone": patient.phone,
        "patient_email": patient.email,
        "message": f"Welcome, {patient.first_name}!"
    }


@router.get("/history/{session_id}")
async def get_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get conversation history for a session."""
    result = await db.execute(
        select(Conversation).where(Conversation.session_id == session_id)
    )
    conversation = result.scalars().first()
    if not conversation:
        return {"messages": []}

    history = await get_conversation_history(conversation.id, db)
    return {"messages": history}

