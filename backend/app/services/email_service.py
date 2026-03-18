"""Email service — SendGrid → Gmail SMTP → File fallback."""
import os
import json
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from app.config import settings

FALLBACK_DIR = Path(__file__).parent.parent.parent / "notifications"


def _ensure_fallback_dir():
    FALLBACK_DIR.mkdir(exist_ok=True)


def _build_html(appointment_data: dict) -> str:
    return f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #0a1628 0%, #0d2137 100%); border-radius: 16px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #0A6EBD 0%, #12A89D 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">✅ Appointment Confirmed</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0;">Kyron Medical Practice</p>
        </div>
        <div style="padding: 30px; color: #e0e0e0;">
            <p style="font-size: 16px;">Hello <strong>{appointment_data['patient_name']}</strong>,</p>
            <p>Your appointment has been successfully scheduled. Here are your details:</p>
            <div style="background: rgba(10, 110, 189, 0.15); border: 1px solid rgba(10, 110, 189, 0.3); border-radius: 12px; padding: 20px; margin: 20px 0;">
                <table style="width: 100%; color: #e0e0e0;">
                    <tr><td style="padding: 8px 0; font-weight: bold; color: #12A89D;">📋 Doctor:</td><td style="padding: 8px 0;">{appointment_data['doctor_name']}</td></tr>
                    <tr><td style="padding: 8px 0; font-weight: bold; color: #12A89D;">🏥 Specialty:</td><td style="padding: 8px 0;">{appointment_data['specialty']}</td></tr>
                    <tr><td style="padding: 8px 0; font-weight: bold; color: #12A89D;">📅 Date & Time:</td><td style="padding: 8px 0;">{appointment_data['date_time']}</td></tr>
                    <tr><td style="padding: 8px 0; font-weight: bold; color: #12A89D;">📝 Reason:</td><td style="padding: 8px 0;">{appointment_data['reason']}</td></tr>
                </table>
            </div>
            <div style="background: rgba(18, 168, 157, 0.15); border: 1px solid rgba(18, 168, 157, 0.3); border-radius: 12px; padding: 16px; margin: 20px 0;">
                <p style="margin: 0; font-size: 14px;">
                    📍 <strong>Location:</strong> 450 Medical Center Drive, Suite 200, San Francisco, CA 94102<br>
                    📞 <strong>Phone:</strong> (415) 555-0100
                </p>
            </div>
            <p style="font-size: 14px; color: #999;">Please arrive 15 minutes before your appointment. If you need to cancel or reschedule, please call our office at least 24 hours in advance.</p>
        </div>
        <div style="background: rgba(0,0,0,0.3); padding: 16px; text-align: center;">
            <p style="color: #666; margin: 0; font-size: 12px;">© 2026 Kyron Medical Practice. All rights reserved.</p>
        </div>
    </div>
    """


def _build_plain_text(appointment_data: dict) -> str:
    return (
        f"Appointment Confirmed — Kyron Medical Practice\n\n"
        f"Hello {appointment_data['patient_name']},\n\n"
        f"Your appointment has been scheduled:\n"
        f"  Doctor:    {appointment_data['doctor_name']}\n"
        f"  Specialty: {appointment_data['specialty']}\n"
        f"  Date/Time: {appointment_data['date_time']}\n"
        f"  Reason:    {appointment_data['reason']}\n\n"
        f"Location: 450 Medical Center Drive, Suite 200, San Francisco, CA 94102\n"
        f"Phone: (415) 555-0100\n\n"
        f"Please arrive 15 minutes early.\n"
        f"To cancel/reschedule, call at least 24 hours in advance.\n\n"
        f"— Kyron Medical Practice"
    )


async def _send_via_smtp(to_email: str, subject: str, html: str, plain: str) -> bool:
    """Send email via Gmail SMTP (or any SMTP server)."""
    msg = MIMEMultipart("alternative")
    msg["From"] = f"Kyron Medical <{settings.smtp_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_email, settings.smtp_password)
        server.send_message(msg)

    print(f"✅ Email sent via SMTP ({settings.smtp_host}) to {to_email}")
    return True


def _save_to_file(to_email: str, subject: str, html: str, appointment_data: dict) -> bool:
    """Fallback: save email to local JSON file."""
    _ensure_fallback_dir()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = FALLBACK_DIR / f"email_{ts}_{to_email.replace('@', '_at_')}.json"

    record = {
        "type": "email",
        "timestamp": datetime.datetime.now().isoformat(),
        "to": to_email,
        "subject": subject,
        "appointment": {k: v for k, v in appointment_data.items()},
        "html_content": html,
    }
    with open(filename, "w") as f:
        json.dump(record, f, indent=2, default=str)

    print(f"📧 [FALLBACK] Email saved to {filename}")
    print(f"   To: {to_email}")
    print(f"   Subject: {subject}")
    return True


async def send_appointment_confirmation(appointment_data: dict) -> bool:
    """Send appointment confirmation — tries SendGrid → Gmail SMTP → File."""
    subject = f"Appointment Confirmed - {appointment_data['doctor_name']} on {appointment_data['date_time']}"
    to_email = appointment_data.get("patient_email", "unknown@example.com")
    html_content = _build_html(appointment_data)
    plain_text = _build_plain_text(appointment_data)

    # ---- 1. SendGrid ----
    if settings.sendgrid_api_key:
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            message = Mail(
                from_email=settings.sendgrid_from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content,
            )
            sg = SendGridAPIClient(settings.sendgrid_api_key)
            response = sg.send(message)
            print(f"✅ Email sent via SendGrid to {to_email}, status: {response.status_code}")
            return response.status_code in (200, 201, 202)
        except Exception as e:
            print(f"❌ SendGrid error: {e}")

    # ---- 2. Gmail SMTP (no domain needed!) ----
    if settings.smtp_email and settings.smtp_password:
        try:
            return await _send_via_smtp(to_email, subject, html_content, plain_text)
        except Exception as e:
            print(f"❌ SMTP error: {e}")

    # ---- 3. File fallback ----
    return _save_to_file(to_email, subject, html_content, appointment_data)
