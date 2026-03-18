"""Voice call service — Twilio with graceful fallback."""
import json
from urllib.parse import urlparse
from app.config import settings
from app.services.local_fallback_store import save_fallback_event


def _get_twilio_client():
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return None
    from twilio.rest import Client
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def _validate_twilio_webhook_base_url(base_url: str) -> tuple[bool, str | None]:
    """Validate APP_BASE_URL for Twilio webhooks.

    Twilio cannot call localhost/private URLs from Twilio cloud infrastructure.
    """
    parsed = urlparse(base_url or "")
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False, "APP_BASE_URL must be a full URL like https://your-domain.com"

    host = (parsed.hostname or "").lower()
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
    if host in blocked_hosts:
        return False, (
            "APP_BASE_URL points to localhost. Twilio requires a public URL. "
            "Use an https tunnel (for example ngrok) or a deployed domain."
        )

    return True, None


def _queue_voice_fallback(phone_number: str, session_id: str, reason: str, details: str = "") -> dict:
    """Persist a voice fallback request locally and return a customer-safe response."""
    file_path = save_fallback_event(
        "voice_call_request",
        {
            "phone_number": phone_number,
            "session_id": session_id,
            "reason": reason,
            "details": details,
        },
    )
    reference = file_path.split("/")[-1] if file_path else None
    return {
        "success": True,
        "queued": True,
        "mode": "fallback_log",
        "reference": reference,
        "message": "Your callback request has been received and logged. Our team will follow up shortly."
    }


async def initiate_voice_call(phone_number: str, session_id: str) -> dict:
    """Initiate an outbound voice call to the patient to continue the chat."""
    client = _get_twilio_client()
    if not client:
        print(f"📞 [FALLBACK] Voice call requested to {phone_number} (session: {session_id}) — Twilio not configured")
        return _queue_voice_fallback(
            phone_number,
            session_id,
            reason="twilio_not_configured",
            details="Twilio credentials are missing",
        )

    base_url = (settings.app_base_url or "").rstrip("/")
    is_valid, validation_error = _validate_twilio_webhook_base_url(base_url)
    if not is_valid:
        print(f"❌ Voice config error: {validation_error}")
        return _queue_voice_fallback(
            phone_number,
            session_id,
            reason="invalid_app_base_url",
            details=validation_error or "APP_BASE_URL validation failed",
        )

    try:
        webhook_url = f"{base_url}/api/voice/webhook?session_id={session_id}"
        call = client.calls.create(
            to=phone_number,
            from_=settings.twilio_phone_number,
            url=webhook_url,
            method="POST",
            status_callback=f"{base_url}/api/voice/status",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
        )
        print(f"📞 Call initiated to {phone_number}, SID: {call.sid}")
        return {"success": True, "call_sid": call.sid}
    except Exception as e:
        print(f"❌ Voice call error: {e}")
        return _queue_voice_fallback(
            phone_number,
            session_id,
            reason="twilio_call_error",
            details=str(e),
        )


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
