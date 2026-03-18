"""Scheduling service - manages appointment slots and booking."""
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import AvailabilitySlot, Doctor, Appointment, Patient


DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6
}


async def get_available_slots(
    doctor_id: int,
    db: AsyncSession,
    preferred_day: str | None = None,
    preferred_time: str | None = None,
    limit: int = 8
) -> list[dict]:
    """Get available slots for a doctor with optional day/time preferences."""
    now = datetime.datetime.now()

    query = select(AvailabilitySlot, Doctor).join(Doctor).where(
        and_(
            AvailabilitySlot.doctor_id == doctor_id,
            AvailabilitySlot.is_booked == False,
            AvailabilitySlot.start_time > now
        )
    ).order_by(AvailabilitySlot.start_time)

    result = await db.execute(query)
    rows = result.all()

    slots = []
    for slot, doctor in rows:
        # Apply day filter
        if preferred_day:
            day_lower = preferred_day.lower()
            if day_lower in DAY_MAP:
                if slot.start_time.weekday() != DAY_MAP[day_lower]:
                    continue

        # Apply time preference filter
        if preferred_time:
            hour = slot.start_time.hour
            if preferred_time.lower() == "morning" and hour >= 12:
                continue
            elif preferred_time.lower() == "afternoon" and (hour < 12 or hour >= 17):
                continue
            elif preferred_time.lower() == "evening" and hour < 16:
                continue

        slots.append({
            "id": slot.id,
            "doctor_name": doctor.name,
            "doctor_specialty": doctor.specialty,
            "start_time": slot.start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": slot.end_time.strftime("%Y-%m-%d %H:%M"),
            "day_of_week": slot.start_time.strftime("%A"),
            "display_date": slot.start_time.strftime("%A, %B %d at %I:%M %p")
        })

        if len(slots) >= limit:
            break

    return slots


async def book_appointment(
    patient_id: int,
    slot_id: int,
    reason: str,
    db: AsyncSession
) -> dict | None:
    """Book an appointment by reserving a slot."""
    # Get the slot
    result = await db.execute(
        select(AvailabilitySlot, Doctor)
        .join(Doctor)
        .where(
            and_(
                AvailabilitySlot.id == slot_id,
                AvailabilitySlot.is_booked == False
            )
        )
    )
    row = result.first()
    if not row:
        return None

    slot, doctor = row

    # Get the patient
    patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalars().first()
    if not patient:
        return None

    # Mark slot as booked
    slot.is_booked = True

    # Create appointment
    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor.id,
        slot_id=slot_id,
        reason=reason,
        status="confirmed"
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    return {
        "id": appointment.id,
        "doctor_name": doctor.name,
        "specialty": doctor.specialty,
        "date_time": slot.start_time.strftime("%A, %B %d, %Y at %I:%M %p"),
        "end_time": slot.end_time.strftime("%I:%M %p"),
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "patient_email": patient.email,
        "patient_phone": patient.phone,
        "patient_sms_opt_in": patient.sms_opt_in,
        "status": "confirmed",
        "reason": reason
    }

