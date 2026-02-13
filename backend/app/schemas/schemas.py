"""Pydantic schemas for request/response validation."""

from datetime import datetime, date, time
from typing import Optional
from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str  # "patient" or "doctor"
    specialization: Optional[str] = None
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str

    model_config = {"from_attributes": True}


# ── Doctor ────────────────────────────────────────────────────────────────────

class DoctorResponse(BaseModel):
    id: int
    name: str
    email: str
    specialization: str
    phone: Optional[str] = None

    model_config = {"from_attributes": True}


class AvailabilitySlot(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str


# ── Appointment ───────────────────────────────────────────────────────────────

class AppointmentCreate(BaseModel):
    doctor_id: int
    appointment_date: date
    start_time: str
    end_time: str
    reason: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: int
    doctor_name: str
    patient_name: str
    appointment_date: date
    start_time: str
    end_time: str
    status: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: int
    actions_taken: list[str] = []


# ── Notifications ─────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    channel: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DoctorReportRequest(BaseModel):
    query: str
    send_notification: bool = True
    notification_channel: str = "slack"  # slack, in_app
