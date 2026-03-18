"""Info routes - office information, service status, and misc endpoints."""
import json
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Doctor
from app.config import settings

router = APIRouter()

NOTIFICATIONS_DIR = Path(__file__).parent.parent.parent / "notifications"


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
    }
}


@router.get("/office")
async def get_office_info():
    """Get office address, hours, and contact information."""
    return OFFICE_INFO


@router.get("/doctors")
async def get_doctors(db: AsyncSession = Depends(get_db)):
    """Get list of all doctors and their specialties."""
    result = await db.execute(select(Doctor))
    doctors = result.scalars().all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "specialty": d.specialty,
            "bio": d.bio
        }
        for d in doctors
    ]


@router.get("/services/status")
async def service_status():
    """Check which services are configured and active."""
    return {
        "ai": {
            "status": "available"
        },
        "email": {
            "provider": "SendGrid" if settings.sendgrid_api_key else ("Gmail SMTP" if settings.smtp_email else "File Fallback"),
            "status": "active" if (settings.sendgrid_api_key or settings.smtp_email) else "fallback (saves to /notifications)"
        },
        "sms": {
            "provider": "Twilio" if settings.twilio_account_sid else "File Fallback",
            "status": "active" if (settings.twilio_account_sid and settings.twilio_auth_token) else "fallback (saves to /notifications)"
        },
        "voice": {
            "provider": "Twilio" if settings.twilio_account_sid else "Not configured",
            "status": "active" if (settings.twilio_account_sid and settings.twilio_phone_number) else "unavailable"
        }
    }


@router.get("/notifications")
async def get_notifications():
    """View saved fallback notifications (emails/SMS that were logged to file)."""
    if not NOTIFICATIONS_DIR.exists():
        return {"notifications": [], "count": 0}

    notifications = []
    for f in sorted(NOTIFICATIONS_DIR.glob("*.json"), reverse=True)[:50]:
        try:
            data = json.loads(f.read_text())
            data["filename"] = f.name
            # Strip HTML for readability
            data.pop("html_content", None)
            notifications.append(data)
        except Exception:
            pass

    return {"notifications": notifications, "count": len(notifications)}


