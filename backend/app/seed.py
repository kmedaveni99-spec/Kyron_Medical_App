"""Seed the database with doctors and availability slots."""
import json
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Doctor, AvailabilitySlot


DOCTORS = [
    {
        "name": "Dr. Maria Rivera",
        "specialty": "Orthopedics",
        "body_parts": json.dumps(["knee", "hip", "shoulder", "elbow", "ankle", "wrist",
                                   "joints", "bones", "back", "spine", "fracture",
                                   "ligament", "tendon", "muscle", "arm", "leg"]),
        "bio": "Board-certified orthopedic surgeon with 15 years of experience specializing in joint replacement and sports medicine."
    },
    {
        "name": "Dr. Raj Patel",
        "specialty": "Cardiology",
        "body_parts": json.dumps(["heart", "chest", "cardiovascular", "blood pressure",
                                   "arteries", "veins", "circulation", "palpitations",
                                   "heartbeat", "cardiac", "cholesterol"]),
        "bio": "Interventional cardiologist focused on preventive heart care and minimally invasive cardiac procedures."
    },
    {
        "name": "Dr. Sarah Kim",
        "specialty": "Dermatology",
        "body_parts": json.dumps(["skin", "rash", "acne", "mole", "eczema", "psoriasis",
                                   "dermatitis", "hair", "nails", "melanoma", "wart",
                                   "hives", "itching", "sunburn", "lesion"]),
        "bio": "Dermatologist specializing in medical and cosmetic dermatology, with expertise in skin cancer screening."
    },
    {
        "name": "Dr. Chidi Okafor",
        "specialty": "Neurology",
        "body_parts": json.dumps(["brain", "nerves", "headache", "migraine", "seizure",
                                   "numbness", "tingling", "memory", "dizziness",
                                   "tremor", "neuropathy", "concussion", "stroke",
                                   "multiple sclerosis", "head"]),
        "bio": "Neurologist with a focus on headache disorders, epilepsy, and neurodegenerative conditions."
    },
    {
        "name": "Dr. Emily Chen",
        "specialty": "Gastroenterology",
        "body_parts": json.dumps(["stomach", "abdomen", "digestive", "intestine", "colon",
                                   "liver", "gallbladder", "acid reflux", "heartburn",
                                   "nausea", "bloating", "constipation", "diarrhea",
                                   "gut", "bowel", "IBS"]),
        "bio": "Gastroenterologist specializing in inflammatory bowel disease and advanced endoscopic procedures."
    },
]


async def seed_database(db: AsyncSession):
    """Seed doctors and their availability slots."""
    # Check if doctors already exist
    result = await db.execute(select(Doctor))
    if result.scalars().first():
        return  # Already seeded

    today = datetime.date.today()
    start_date = today + datetime.timedelta(days=1)  # Start from tomorrow

    for doc_data in DOCTORS:
        doctor = Doctor(**doc_data)
        db.add(doctor)
        await db.flush()

        # Generate availability slots for the next 45 days
        for day_offset in range(1, 46):
            slot_date = start_date + datetime.timedelta(days=day_offset)

            # Skip Sundays
            if slot_date.weekday() == 6:
                continue

            # Saturday: limited hours (9 AM - 1 PM)
            if slot_date.weekday() == 5:
                hours = [(9, 0), (9, 30), (10, 0), (10, 30), (11, 0), (11, 30), (12, 0), (12, 30)]
            else:
                # Weekdays: 8 AM - 5 PM with 30-minute slots
                hours = [(h, m) for h in range(8, 17) for m in (0, 30)]
                # Remove lunch hour
                hours = [(h, m) for h, m in hours if not (12 <= h < 13)]

            for hour, minute in hours:
                start_time = datetime.datetime(
                    slot_date.year, slot_date.month, slot_date.day,
                    hour, minute, 0
                )
                end_time = start_time + datetime.timedelta(minutes=30)

                slot = AvailabilitySlot(
                    doctor_id=doctor.id,
                    start_time=start_time,
                    end_time=end_time,
                    is_booked=False
                )
                db.add(slot)

    await db.commit()
    print("✅ Database seeded with doctors and availability slots.")

