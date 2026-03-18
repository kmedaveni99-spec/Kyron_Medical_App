"""SMS service — Twilio with console/file fallback."""
import json
import datetime
from pathlib import Path
from app.config import settings

FALLBACK_DIR = Path(__file__).parent.parent.parent / "notifications"


def _ensure_fallback_dir():
    FALLBACK_DIR.mkdir(exist_ok=True)


def _get_twilio_client():
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return None
    from twilio.rest import Client
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def _build_sms_body(appointment_data: dict) -> str:
    return (
        f"✅ Kyron Medical - Appointment Confirmed!\n\n"
        f"Doctor: {appointment_data['doctor_name']}\n"
        f"Date: {appointment_data['date_time']}\n"
        f"Reason: {appointment_data['reason']}\n\n"
        f"📍 450 Medical Center Dr, Suite 200, SF, CA 94102\n"
        f"📞 (415) 555-0100\n\n"
        f"Please arrive 15 min early. Reply STOP to opt out."
    )


async def send_appointment_sms(appointment_data: dict) -> bool:
    """Send appointment confirmation SMS — uses Twilio or logs to file."""
    if not appointment_data.get("patient_sms_opt_in"):
        print("ℹ️  Patient has not opted in for SMS — skipping.")
        return False

    phone = appointment_data.get("patient_phone", "")
    if not phone:
        print("ℹ️  No patient phone number — skipping SMS.")
        return False

    body = _build_sms_body(appointment_data)

    # ---- Twilio path ----
    client = _get_twilio_client()
    if client and settings.twilio_phone_number:
        try:
            message = client.messages.create(
                body=body,
                from_=settings.twilio_phone_number,
                to=phone,
            )
            print(f"✅ SMS sent via Twilio to {phone}, SID: {message.sid}")
            return True
        except Exception as e:
            print(f"❌ Twilio SMS error: {e} — falling back to file log")

    # ---- Fallback: log to console + save to file ----
    _ensure_fallback_dir()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_phone = phone.replace("+", "").replace(" ", "_") or "unknown"
    filename = FALLBACK_DIR / f"sms_{ts}_{safe_phone}.json"

    record = {
        "type": "sms",
        "timestamp": datetime.datetime.now().isoformat(),
        "to": phone,
        "body": body,
        "appointment": {k: v for k, v in appointment_data.items()},
    }

    with open(filename, "w") as f:
        json.dump(record, f, indent=2, default=str)

    print(f"📱 [FALLBACK] SMS saved to {filename}")
    print(f"   To: {phone}")
    print(f"   Body: {body[:80]}...")
    return True
