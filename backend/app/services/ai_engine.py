"""AI Conversational Engine — multi-provider: OpenAI / Groq / Gemini / Mock fallback."""
import json
import re
import datetime
from typing import Optional
from openai import AsyncOpenAI
from app.config import settings

# --------------- Provider Setup ---------------
# Priority: OpenAI -> Groq -> Gemini -> Mock
# Groq uses the OpenAI-compatible API, so the same client interface works.

AVAILABLE_PROVIDERS: list[dict] = []

if settings.openai_api_key:
    AVAILABLE_PROVIDERS.append({
        "name": "openai",
        "model": "gpt-4o-mini",
        "client": AsyncOpenAI(api_key=settings.openai_api_key),
    })

if settings.groq_api_key:
    AVAILABLE_PROVIDERS.append({
        "name": "groq",
        "model": "llama-3.3-70b-versatile",
        "client": AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1"
        ),
    })

if settings.google_api_key:
    AVAILABLE_PROVIDERS.append({
        "name": "gemini",
        "model": "gemini-2.0-flash",
        "client": None,
    })

if AVAILABLE_PROVIDERS:
    PROVIDER = AVAILABLE_PROVIDERS[0]["name"]
    MODEL = AVAILABLE_PROVIDERS[0]["model"]
    chain = " -> ".join([f"{p['name']} ({p['model']})" for p in AVAILABLE_PROVIDERS])
    print(f"AI provider chain: {chain}")
else:
    PROVIDER = "mock"
    MODEL = ""
    print("No AI API key configured - using mock AI")

USE_MOCK = not AVAILABLE_PROVIDERS
LAST_SUCCESSFUL_PROVIDER: dict | None = None


def _set_last_successful_provider(provider: dict):
    """Persist the most recent successful provider call for observability."""
    global LAST_SUCCESSFUL_PROVIDER
    LAST_SUCCESSFUL_PROVIDER = {
        "name": provider["name"],
        "model": provider["model"],
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }


def get_ai_runtime_status() -> dict:
    """Return configured provider chain and last success metadata."""
    return {
        "provider_chain": [{
            "name": p["name"],
            "model": p["model"]
        } for p in AVAILABLE_PROVIDERS],
        "last_successful_provider": LAST_SUCCESSFUL_PROVIDER,
    }

SYSTEM_PROMPT = """You are Kyron, a friendly and professional AI medical assistant for Kyron Medical Practice. You help patients with:

1. **Scheduling Appointments**: Collect patient information and help them book with the right doctor.
2. **Prescription Refill Inquiries**: Check on refill status (use check_rx_status tool).
3. **Office Information**: Provide office hours, address, and provider information (use get_office_info tool).

IMPORTANT RULES:
- You CANNOT provide medical advice, diagnoses, or treatment recommendations. If asked, politely explain that you're an assistant and they should speak with a doctor.
- NEVER say anything that could be interpreted as a medical diagnosis or treatment plan.
- Be warm, empathetic, and conversational - like talking to a helpful front desk receptionist.
- Keep responses concise (2-3 sentences max when possible).

APPOINTMENT SCHEDULING WORKFLOW — follow these steps IN ORDER:
1. First, ask the patient what they want to be seen for. DO NOT call any tool yet.
2. Then ask for their FULL information: first name, last name, date of birth, phone number, and email. DO NOT call collect_patient_intake until the patient has provided ALL of this information in the conversation.
3. ONLY after you have ALL 5 pieces of info (first name, last name, DOB, phone, email), call collect_patient_intake.
4. After intake, call match_doctor_specialty with their reason.
5. Then call get_available_slots for that doctor.
6. Let the patient choose a slot, then call book_appointment.
- NEVER invent or guess patient information. You must ask and wait for the patient to provide it.
- If someone asks about a body part/condition your practice doesn't treat, let them know politely.

Your practice has these departments: Orthopedics, Cardiology, Dermatology, Neurology, and Gastroenterology.

Today's date is {today}. When discussing dates, use natural language (e.g., "Tuesday, March 24th") rather than raw date formats.

Start by warmly greeting the patient and asking how you can help."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "collect_patient_intake",
            "description": "Collect patient information for registration. Call this when you have gathered the patient's first name, last name, date of birth, phone number, email, and reason for visit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string", "description": "Patient's first name"},
                    "last_name": {"type": "string", "description": "Patient's last name"},
                    "date_of_birth": {"type": "string", "description": "Patient's date of birth in YYYY-MM-DD format"},
                    "phone": {"type": "string", "description": "Patient's phone number"},
                    "email": {"type": "string", "description": "Patient's email address"},
                    "reason": {"type": "string", "description": "Reason for the appointment"},
                    "sms_opt_in": {"type": "boolean", "description": "Whether patient opted in for SMS notifications"}
                },
                "required": ["first_name", "last_name", "date_of_birth", "phone", "email", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "match_doctor_specialty",
            "description": "Match the patient's health concern to the appropriate doctor specialty.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "The patient's reason for visit or health concern"}
                },
                "required": ["reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Get available appointment time slots for a specific doctor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "integer", "description": "The ID of the doctor"},
                    "preferred_day": {"type": "string", "description": "Optional: preferred day of week (e.g. 'Tuesday')"},
                    "preferred_time": {"type": "string", "description": "Optional: 'morning', 'afternoon', or 'evening'"}
                },
                "required": ["doctor_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment for the patient with the selected time slot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "slot_id": {"type": "integer", "description": "The ID of the availability slot to book"},
                    "reason": {"type": "string", "description": "Reason for the appointment"}
                },
                "required": ["slot_id", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_rx_status",
            "description": "Check the status of a prescription refill for the patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medication_name": {"type": "string", "description": "Name of the medication to check"}
                },
                "required": ["medication_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_office_info",
            "description": "Get office information including address, hours, and provider list.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


# =============================================
# MOCK / FALLBACK AI ENGINE
# =============================================

MOCK_BODY_KEYWORDS = {
    "orthopedics": ["knee", "hip", "shoulder", "elbow", "ankle", "wrist", "joint",
                     "bone", "back", "spine", "fracture", "muscle", "arm", "leg", "neck", "foot"],
    "cardiology": ["heart", "chest", "blood pressure", "palpitation", "cardiac", "breathing"],
    "dermatology": ["skin", "rash", "acne", "mole", "eczema", "itch", "hair", "nail"],
    "neurology": ["brain", "headache", "migraine", "seizure", "numbness", "dizzy", "nerve", "head", "memory"],
    "gastroenterology": ["stomach", "abdomen", "digestive", "nausea", "bloating", "liver", "bowel", "gut"]
}


class MockConversationState:
    def __init__(self):
        self.stage = "greeting"
        self.collected = {}
        self.matched_specialty = None


mock_states: dict[str, MockConversationState] = {}


def _get_mock_state(session_id: str) -> MockConversationState:
    if session_id not in mock_states:
        mock_states[session_id] = MockConversationState()
    return mock_states[session_id]


async def get_mock_response(user_message: str, session_id: str = "",
                             conversation_history: list = None, session_context: dict = None):
    """Rule-based mock AI for when OpenAI API is unavailable."""
    msg = user_message.lower().strip()
    state = _get_mock_state(session_id)
    ctx = session_context or {}

    # Greetings
    if state.stage == "greeting" or msg in ["hello", "hi", "hey", "help", "start", ""]:
        state.stage = "asked_reason"
        return (
            "Hello! 👋 Welcome to Kyron Medical Practice. I'm Kyron, your AI assistant. "
            "I can help you with scheduling appointments, checking prescription refills, "
            "or finding our office information. How can I help you today?"
        ), None

    # Office info
    office_kw = ["office", "hours", "address", "location", "where", "when", "open", "close", "phone", "contact"]
    if any(kw in msg for kw in office_kw):
        return "", [{"id": "mock_1", "name": "get_office_info", "arguments": {}}]

    # Prescription
    rx_kw = ["prescription", "refill", "medication", "medicine", "rx", "drug", "pill"]
    if any(kw in msg for kw in rx_kw):
        for med in ["lisinopril", "metformin", "atorvastatin", "omeprazole", "sertraline"]:
            if med in msg:
                return "", [{"id": "mock_2", "name": "check_rx_status", "arguments": {"medication_name": med}}]
        return ("Of course! Which medication would you like me to check on? "
                "We have records for Lisinopril, Metformin, Atorvastatin, Omeprazole, and Sertraline."), None

    # Medical advice guard
    advice_kw = ["diagnose", "diagnosis", "treatment", "should i take", "what medicine", "prescribe", "cure"]
    if any(kw in msg for kw in advice_kw):
        return (
            "I appreciate your concern, but I'm not able to provide medical advice or diagnoses. "
            "I'm here to help you schedule an appointment with one of our specialists who can properly "
            "assess your condition. Would you like me to help you book an appointment?"
        ), None

    # Scheduling - detect body part
    schedule_kw = ["schedule", "appointment", "book", "see a doctor", "visit", "check-up", "checkup"]
    if any(kw in msg for kw in schedule_kw) or state.stage in ["asked_reason", "collecting_info"]:
        detected = None
        for specialty, keywords in MOCK_BODY_KEYWORDS.items():
            if any(kw in msg for kw in keywords):
                detected = specialty
                break

        if detected:
            state.matched_specialty = detected
            state.stage = "collecting_info"
            return (
                f"I'd be happy to help you schedule an appointment! Based on what you've described, "
                f"I'd recommend you see our {detected.title()} specialist. "
                f"To get you set up, could you please provide your:\n\n"
                f"• Full name\n• Date of birth\n• Phone number\n• Email address\n\n"
                f"You can share all of this in one message!"
            ), None

        if state.stage == "asked_reason":
            state.stage = "collecting_info"
            return (
                "I'd be happy to help you schedule an appointment! "
                "Could you tell me what you'd like to be seen for? For example, "
                "are you having issues with your joints, heart, skin, head, or stomach?"
            ), None

    # Collecting patient info
    if state.stage == "collecting_info":
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', msg)
        if email_match:
            state.collected["email"] = email_match.group()
        phone_match = re.search(r'[\(]?\d{3}[\)]?[-.\s]?\d{3}[-.\s]?\d{4}', msg)
        if phone_match:
            state.collected["phone"] = phone_match.group()
        dob_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', msg)
        if dob_match:
            state.collected["dob"] = dob_match.group()
        words = user_message.split()
        name_words = [w for w in words if len(w) > 1 and w[0].isupper() and w.isalpha()]
        if name_words and "first_name" not in state.collected:
            state.collected["first_name"] = name_words[0]
            if len(name_words) > 1:
                state.collected["last_name"] = name_words[1]

        needed = []
        if "first_name" not in state.collected:
            needed.append("full name")
        if "dob" not in state.collected:
            needed.append("date of birth")
        if "phone" not in state.collected:
            needed.append("phone number")
        if "email" not in state.collected:
            needed.append("email address")

        if needed:
            return f"Thank you! I still need your {', '.join(needed)}. Could you provide that?", None

        state.stage = "has_info"
        return "", [{
            "id": "mock_intake",
            "name": "collect_patient_intake",
            "arguments": {
                "first_name": state.collected.get("first_name", "Patient"),
                "last_name": state.collected.get("last_name", "User"),
                "date_of_birth": state.collected.get("dob", "1990-01-01"),
                "phone": state.collected.get("phone", "+15551234567"),
                "email": state.collected.get("email", "patient@example.com"),
                "reason": state.matched_specialty or "general checkup",
                "sms_opt_in": False
            }
        }]

    # After intake -> match doctor
    if state.stage == "has_info":
        reason = state.matched_specialty or "general checkup"
        state.stage = "matching"
        return "", [{"id": "mock_match", "name": "match_doctor_specialty", "arguments": {"reason": reason}}]

    # After matching -> show slots
    if state.stage == "matching":
        doctor = ctx.get("matched_doctor", {})
        doctor_id = doctor.get("id", 1)
        preferred_day = None
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]:
            if day in msg:
                preferred_day = day.title()
        state.stage = "showing_slots"
        args = {"doctor_id": doctor_id}
        if preferred_day:
            args["preferred_day"] = preferred_day
        return "", [{"id": "mock_slots", "name": "get_available_slots", "arguments": args}]

    # Slot selection
    if state.stage == "showing_slots":
        slot_match = re.search(r'slot\s*(?:id[:\s]*)?\s*(\d+)', msg)
        if slot_match:
            slot_id = int(slot_match.group(1))
            state.stage = "booking"
            return "", [{"id": "mock_book", "name": "book_appointment",
                         "arguments": {"slot_id": slot_id, "reason": state.matched_specialty or "appointment"}}]
        return ("Great choice! Could you confirm by telling me the specific date and time, "
                "or click one of the available slots above?"), None

    # Default
    return (
        "I'm here to help! I can assist you with:\n\n"
        "🗓 **Scheduling an appointment** — Just tell me what you'd like to be seen for\n"
        "💊 **Prescription refills** — Ask me about your medication status\n"
        "📍 **Office information** — Hours, address, and provider info\n\n"
        "What would you like help with?"
    ), None


async def _mock_tool_result_response(tool_results, session_context=None, session_id=""):
    """Generate mock responses after tool execution."""
    ctx = session_context or {}
    state = _get_mock_state(session_id)

    for result in tool_results:
        data = result.get("result", {})

        if data.get("patient_id") and not ctx.get("matched_doctor"):
            name = data.get("message", "Patient registered")
            state.stage = "has_info"
            reason = state.matched_specialty or "general checkup"
            return (f"✅ {name} Now let me find the best specialist for you...",
                    [{"id": "mock_match", "name": "match_doctor_specialty", "arguments": {"reason": reason}}])

        if data.get("doctor") and not ctx.get("appointment"):
            doctor = data["doctor"]
            state.stage = "matching"
            return (f"Great news! I've matched you with **{doctor['name']}** ({doctor['specialty']}). "
                    f"{doctor.get('bio', '')} Let me check their available time slots...",
                    [{"id": "mock_slots", "name": "get_available_slots", "arguments": {"doctor_id": doctor["id"]}}])

        if data.get("slots"):
            slots = data["slots"]
            slot_list = "\n".join([f"• {s['display_date']}" for s in slots[:6]])
            state.stage = "showing_slots"
            return (f"Here are the available appointments:\n\n{slot_list}\n\n"
                    f"Which time works best for you? You can also ask for a specific day, "
                    f"like \"Do you have something on a Tuesday?\""), None

        if data.get("appointment"):
            appt = data["appointment"]
            state.stage = "booked"
            return (f"🎉 Wonderful! Your appointment is confirmed!\n\n"
                    f"📋 **{appt['doctor_name']}** ({appt['specialty']})\n"
                    f"📅 {appt['date_time']}\n"
                    f"📍 450 Medical Center Dr, Suite 200, SF, CA 94102\n\n"
                    f"A confirmation has been sent to {appt.get('patient_email', 'your email')}. "
                    f"Please arrive 15 minutes early. Is there anything else I can help with?"), None

        if data.get("office"):
            office = data["office"]
            hours_str = "\n".join([f"  {day}: {time}" for day, time in office["hours"].items()])
            providers_str = "\n".join([f"  • {p['name']} — {p['specialty']}" for p in office.get("providers", [])])
            return (f"📍 **{office['name']}**\n\n"
                    f"**Address:** {office['address']}\n**Phone:** {office['phone']}\n\n"
                    f"**Hours:**\n{hours_str}\n\n**Our Providers:**\n{providers_str}\n\n"
                    f"Is there anything else I can help you with?"), None

        if data.get("prescription"):
            rx = data["prescription"]
            return (f"💊 **{rx['medication']}** — Status: **{rx['status']}**\n\n"
                    f"Pharmacy: {rx.get('pharmacy', 'N/A')}\n"
                    f"Refills remaining: {rx.get('refills_remaining', 'N/A')}\n"
                    f"Last filled: {rx.get('last_filled', 'N/A')}\n\n"
                    f"Is there anything else I can help you with?"), None

        if not data.get("success") and data.get("message"):
            return data["message"], None

    return "I've processed that for you. Is there anything else I can help with?", None


# =============================================
# UNIFIED AI FUNCTIONS (OpenAI / Groq / Gemini)
# =============================================

def _build_messages(conversation_history, session_context=None):
    """Build the messages list with system prompt and context."""
    today = datetime.date.today().strftime("%A, %B %d, %Y")
    system_msg = {"role": "system", "content": SYSTEM_PROMPT.format(today=today)}
    if session_context:
        ctx_str = "\n\nCurrent session context:\n"
        if session_context.get("patient"):
            p = session_context["patient"]
            ctx_str += f"- Patient: {p.get('first_name', '')} {p.get('last_name', '')} (ID: {p.get('id', 'N/A')})\n"
            ctx_str += f"- Phone: {p.get('phone', 'N/A')}, Email: {p.get('email', 'N/A')}\n"
        if session_context.get("matched_doctor"):
            d = session_context["matched_doctor"]
            ctx_str += f"- Matched Doctor: {d.get('name', '')} ({d.get('specialty', '')}), Doctor ID: {d.get('id', '')}\n"
        if session_context.get("appointment"):
            a = session_context["appointment"]
            ctx_str += f"- Booked Appointment: {a.get('date_time', '')} with {a.get('doctor_name', '')}\n"
        system_msg["content"] += ctx_str
    return [system_msg] + conversation_history


def _parse_tool_calls(message):
    """Parse tool calls, handling Groq's 'null' arguments edge case."""
    tool_calls = []
    for tc in message.tool_calls:
        raw_args = tc.function.arguments or "{}"
        try:
            args = json.loads(raw_args) if raw_args != "null" else {}
        except (json.JSONDecodeError, TypeError):
            args = {}
        tool_calls.append({"id": tc.id, "name": tc.function.name, "arguments": args or {}})
    return tool_calls


async def _call_openai_compatible(provider: dict, messages, use_tools=True):
    """Call an OpenAI-compatible provider (OpenAI or Groq)."""
    kwargs = dict(model=provider["model"], messages=messages, temperature=0.7, max_tokens=1000)
    if use_tools:
        kwargs["tools"] = TOOLS
        kwargs["tool_choice"] = "auto"
    response = await provider["client"].chat.completions.create(**kwargs)
    message = response.choices[0].message
    if message.tool_calls:
        return message.content or "", _parse_tool_calls(message)
    return message.content or "", None


async def _call_gemini(provider: dict, messages, use_tools=True):
    """Call Google Gemini API."""
    import google.generativeai as genai
    genai.configure(api_key=settings.google_api_key)

    system_text = ""
    gemini_history = []
    for msg in messages:
        if msg["role"] == "system":
            system_text = msg["content"]
        elif msg["role"] == "user":
            gemini_history.append({"role": "user", "parts": [msg["content"]]})
        elif msg["role"] == "assistant":
            gemini_history.append({"role": "model", "parts": [msg.get("content", "") or "OK"]})

    model = genai.GenerativeModel(provider["model"], system_instruction=system_text or None)
    chat = model.start_chat(history=gemini_history[:-1] if gemini_history else [])
    last_msg = gemini_history[-1]["parts"][0] if gemini_history else "Hello"
    response = await chat.send_message_async(last_msg)
    return response.text or "", None


async def _call_provider(provider: dict, messages, use_tools=True):
    """Dispatch call to the appropriate provider implementation."""
    if provider["name"] in ("openai", "groq"):
        return await _call_openai_compatible(provider, messages, use_tools=use_tools)
    if provider["name"] == "gemini":
        if any(msg.get("role") == "tool" for msg in messages):
            raise RuntimeError("Gemini does not support tool-role continuation payloads")
        return await _call_gemini(provider, messages, use_tools=use_tools)
    raise ValueError(f"Unsupported provider: {provider['name']}")


async def _try_provider_chain(messages, use_tools=True):
    """Try providers in order and fail over on errors."""
    last_error = None

    for idx, provider in enumerate(AVAILABLE_PROVIDERS):
        try:
            reply, tool_calls = await _call_provider(provider, messages, use_tools=use_tools)
            _set_last_successful_provider(provider)
            if idx > 0:
                print(f"Provider failover succeeded on {provider['name']} ({provider['model']})")
            return reply, tool_calls
        except Exception as e:
            last_error = e
            print(f"{provider['name']} error: {e}")

    if last_error:
        print("All configured AI providers failed; falling back to mock AI")
    return None


async def get_ai_response(
    conversation_history: list[dict],
    session_context: Optional[dict] = None,
    session_id: str = ""
) -> tuple[str, Optional[list[dict]]]:
    """Get AI response — tries configured provider, falls back to mock."""
    user_message = ""
    if conversation_history:
        for m in reversed(conversation_history):
            if m.get("role") == "user":
                user_message = m.get("content", "")
                break

    if USE_MOCK:
        return await get_mock_response(user_message, session_id, conversation_history, session_context)

    messages = _build_messages(conversation_history, session_context)
    result = await _try_provider_chain(messages, use_tools=True)
    if result:
        return result

    return await get_mock_response(user_message, session_id, conversation_history, session_context)


async def get_ai_response_with_tool_results(
    conversation_history: list[dict],
    tool_results: list[dict],
    original_tool_calls: list,
    session_context: Optional[dict] = None,
    session_id: str = ""
) -> tuple[str, Optional[list[dict]]]:
    """Continue conversation after tool execution."""
    if USE_MOCK:
        return await _mock_tool_result_response(tool_results, session_context, session_id)

    messages = _build_messages(conversation_history, session_context)

    llm_messages = list(messages)
    llm_messages.append({
        "role": "assistant",
        "tool_calls": [{"id": tc["id"], "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])}}
                       for tc in original_tool_calls]
    })
    for result in tool_results:
        llm_messages.append({
            "role": "tool",
            "tool_call_id": result["tool_call_id"],
            "content": json.dumps(result["result"])
        })

    result = await _try_provider_chain(llm_messages, use_tools=True)
    if result:
        return result

    # Last resort: text-only continuation for providers that do not support tool message format.
    gemini = next((p for p in AVAILABLE_PROVIDERS if p["name"] == "gemini"), None)
    if gemini:
        try:
            gemini_messages = list(messages)
            results_text = "Tool results:\n" + "\n".join(json.dumps(r["result"]) for r in tool_results)
            gemini_messages.append({"role": "user", "content": results_text + "\nPlease respond to the patient."})
            reply, tool_calls = await _call_gemini(gemini, gemini_messages, use_tools=False)
            _set_last_successful_provider(gemini)
            return reply, tool_calls
        except Exception as e:
            print(f"gemini fallback error: {e}")

    return await _mock_tool_result_response(tool_results, session_context, session_id)
