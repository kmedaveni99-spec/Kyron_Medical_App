from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    action: Optional[str] = None  # e.g. 'show_intake_form', 'show_slots', 'appointment_booked'
    data: Optional[dict] = None


class PatientIntake(BaseModel):
    session_id: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: str  # YYYY-MM-DD
    phone: str
    email: str
    reason: str
    sms_opt_in: bool = False


class SlotResponse(BaseModel):
    id: int
    doctor_name: str
    doctor_specialty: str
    start_time: str
    end_time: str
    day_of_week: str


class BookAppointmentRequest(BaseModel):
    session_id: str
    patient_id: int
    slot_id: int
    reason: str


class AppointmentResponse(BaseModel):
    id: int
    doctor_name: str
    specialty: str
    date_time: str
    patient_name: str
    status: str


class VoiceCallRequest(BaseModel):
    session_id: str
    phone_number: str


class OfficeInfoResponse(BaseModel):
    name: str
    address: str
    phone: str
    hours: dict
    providers: List[dict]

