"""
Appointment routes - Direct REST API for appointment management.

These routes complement the AI agent by providing direct CRUD operations
for appointments, doctors, and availability data.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.models import (
    User, Doctor, Patient, Appointment, DoctorAvailability,
    AppointmentStatus, UserRole
)
from app.schemas.schemas import DoctorResponse, AppointmentResponse

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


@router.get("/doctors", response_model=list[DoctorResponse])
async def list_doctors(db: AsyncSession = Depends(get_db)):
    """List all doctors with their profiles."""
    result = await db.execute(
        select(Doctor).options(joinedload(Doctor.user))
    )
    doctors = result.unique().scalars().all()
    return [
        DoctorResponse(
            id=d.id,
            name=d.user.name,
            email=d.user.email,
            specialization=d.specialization,
            phone=d.phone,
        )
        for d in doctors
    ]


@router.get("/my-appointments")
async def my_appointments(
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's appointments."""
    if user.role == UserRole.DOCTOR:
        query = (
            select(Appointment)
            .options(
                joinedload(Appointment.patient).joinedload(Patient.user),
                joinedload(Appointment.doctor).joinedload(Doctor.user),
            )
            .where(Appointment.doctor_id == user.doctor_profile.id)
        )
    else:
        query = (
            select(Appointment)
            .options(
                joinedload(Appointment.doctor).joinedload(Doctor.user),
                joinedload(Appointment.patient).joinedload(Patient.user),
            )
            .where(Appointment.patient_id == user.patient_profile.id)
        )

    if status:
        query = query.where(Appointment.status == status)

    query = query.order_by(Appointment.appointment_date.desc(), Appointment.start_time)
    result = await db.execute(query)
    appointments = result.unique().scalars().all()

    return [
        {
            "id": a.id,
            "doctor_name": a.doctor.user.name,
            "patient_name": a.patient.user.name,
            "date": str(a.appointment_date),
            "start_time": a.start_time.strftime("%H:%M"),
            "end_time": a.end_time.strftime("%H:%M"),
            "status": a.status.value,
            "reason": a.reason,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in appointments
    ]


@router.get("/doctor-stats")
async def doctor_stats(
    date_from: str | None = None,
    date_to: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get appointment statistics for the logged-in doctor."""
    if user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Only doctors can access stats")

    from app.mcp_server.tool_handlers import ToolHandlers
    handlers = ToolHandlers(db)

    args = {"doctor_id": user.doctor_profile.id}
    if date_from:
        args["date_from"] = date_from
    if date_to:
        args["date_to"] = date_to

    return await handlers.get_appointment_stats(args)
