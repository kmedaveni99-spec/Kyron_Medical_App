"""Doctor matching service - matches patient complaints to doctor specialties."""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Doctor


# Keyword-based specialty matching with synonyms and related terms
SPECIALTY_KEYWORDS = {
    "Orthopedics": [
        "knee", "hip", "shoulder", "elbow", "ankle", "wrist", "joint", "joints",
        "bone", "bones", "back", "spine", "fracture", "ligament", "tendon",
        "muscle", "arm", "leg", "sports injury", "sprain", "strain", "arthritis",
        "cartilage", "osteoporosis", "scoliosis", "sciatica", "rotator cuff",
        "meniscus", "ACL", "torn", "broken", "foot", "hand", "neck pain",
        "stiff", "stiffness", "physical therapy", "orthopedic"
    ],
    "Cardiology": [
        "heart", "chest", "cardiovascular", "blood pressure", "hypertension",
        "artery", "arteries", "vein", "veins", "circulation", "palpitation",
        "palpitations", "heartbeat", "cardiac", "cholesterol", "irregular",
        "shortness of breath", "breathing", "angina", "heart attack",
        "murmur", "valve", "atrial", "fibrillation", "EKG", "ECG"
    ],
    "Dermatology": [
        "skin", "rash", "acne", "mole", "eczema", "psoriasis", "dermatitis",
        "hair loss", "nail", "nails", "melanoma", "wart", "hives", "itching",
        "itchy", "sunburn", "lesion", "bump", "blemish", "discoloration",
        "dry skin", "oily", "fungal", "ringworm", "eczema", "spots",
        "freckle", "cyst", "boil", "blister", "scar"
    ],
    "Neurology": [
        "brain", "nerve", "nerves", "headache", "migraine", "seizure",
        "numbness", "tingling", "memory", "dizziness", "dizzy", "tremor",
        "neuropathy", "concussion", "stroke", "multiple sclerosis", "MS",
        "head", "cognitive", "confusion", "epilepsy", "vertigo",
        "parkinson", "alzheimer", "dementia", "fainting", "blackout"
    ],
    "Gastroenterology": [
        "stomach", "abdomen", "abdominal", "digestive", "intestine", "colon",
        "liver", "gallbladder", "acid reflux", "heartburn", "nausea",
        "bloating", "constipation", "diarrhea", "gut", "bowel", "IBS",
        "crohn", "ulcer", "gastric", "vomiting", "indigestion", "appetite",
        "swallowing", "esophagus", "rectal", "hemorrhoid", "celiac"
    ]
}


async def match_doctor(reason: str, db: AsyncSession) -> dict | None:
    """Match a patient's reason/complaint to the best doctor."""
    reason_lower = reason.lower()

    # Score each specialty
    scores = {}
    for specialty, keywords in SPECIALTY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in reason_lower)
        if score > 0:
            scores[specialty] = score

    if not scores:
        return None

    # Get the best matching specialty
    best_specialty = max(scores, key=scores.get)

    # Find the doctor with that specialty
    result = await db.execute(
        select(Doctor).where(Doctor.specialty == best_specialty)
    )
    doctor = result.scalars().first()

    if doctor:
        return {
            "id": doctor.id,
            "name": doctor.name,
            "specialty": doctor.specialty,
            "bio": doctor.bio,
            "body_parts": json.loads(doctor.body_parts)
        }

    return None

