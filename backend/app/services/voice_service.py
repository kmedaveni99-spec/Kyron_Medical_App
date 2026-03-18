"""Voice call service — Twilio with graceful fallback."""
import json
from app.config import settings


def _get_twilio_client():
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return None
    from twilio.rest import Client
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


async def initiate_voice_call(phone_number: str, session_id: str) -> dict:
    """Initiate an outbound voice call to the patient to continue the chat."""
    client = _get_twilio_client()
    if not client:
        print(f"📞 [FALLBACK] Voice call requested to {phone_number} (session: {session_id}) — Twilio not configured")
        return {
            "success": False,
            "error": "Voice calling is not configured yet. Please call our office at (415) 555-0100 to continue your conversation."
        }

    try:
        webhook_url = f"{settings.app_base_url}/api/voice/webhook?session_id={session_id}"
        call = client.calls.create(
            to=phone_number,
            from_=settings.twilio_phone_number,
            url=webhook_url,
            method="POST",
            status_callback=f"{settings.app_base_url}/api/voice/status",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
        )
        print(f"📞 Call initiated to {phone_number}, SID: {call.sid}")
        return {"success": True, "call_sid": call.sid}
    except Exception as e:
        print(f"❌ Voice call error: {e}")
        return {"success": False, "error": str(e)}


def generate_greeting_twiml(session_id: str, conversation_summary: str = "") -> str:
    """Generate TwiML for the voice call greeting."""
    from twilio.twiml.voice_response import VoiceResponse, Gather
    response = VoiceResponse()

    greeting = (
        "Hello! This is Kyron, your medical assistant from Kyron Medical Practice. "
        "I'm continuing our conversation from the web chat. "
    )
    if conversation_summary:
        greeting += f"Here's where we left off: {conversation_summary}. "
    greeting += "How can I help you?"

    gather = Gather(
        input="speech",
        action=f"{settings.app_base_url}/api/voice/respond?session_id={session_id}",
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say(greeting, voice="Polly.Joanna", language="en-US")
    response.append(gather)

    response.say("I didn't catch that. Please try again.", voice="Polly.Joanna")
    response.redirect(f"{settings.app_base_url}/api/voice/webhook?session_id={session_id}")
    return str(response)


def generate_response_twiml(ai_response: str, session_id: str) -> str:
    """Generate TwiML with AI response and gather next input."""
    from twilio.twiml.voice_response import VoiceResponse, Gather
    response = VoiceResponse()

    gather = Gather(
        input="speech",
        action=f"{settings.app_base_url}/api/voice/respond?session_id={session_id}",
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say(ai_response, voice="Polly.Joanna", language="en-US")
    response.append(gather)

    response.say("Are you still there? Feel free to say something or hang up if you're all set.", voice="Polly.Joanna")
    response.redirect(f"{settings.app_base_url}/api/voice/webhook?session_id={session_id}")
    return str(response)
