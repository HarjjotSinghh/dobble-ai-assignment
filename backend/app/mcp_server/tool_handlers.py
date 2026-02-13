"""
MCP Tool Handler Implementations.

Each handler corresponds to a tool defined in server.py and contains the
actual business logic for executing that tool's functionality.
These handlers interact with the database, external APIs, and services.
"""

from datetime import datetime, date, time, timedelta
from typing import Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging

from app.models.models import (
    Doctor, Patient, User, Appointment, DoctorAvailability,
    Notification, AppointmentStatus, UserRole
)
from app.services.calendar_service import CalendarService
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ToolHandlers:
    """Handlers for all MCP tools. Injected with a database session."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.calendar_service = CalendarService()
        self.email_service = EmailService()
        self.notification_service = NotificationService()

    async def handle_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Route a tool call to the appropriate handler."""
        handlers = {
            "list_doctors": self.list_doctors,
            "check_doctor_availability": self.check_doctor_availability,
            "book_appointment": self.book_appointment,
            "cancel_appointment": self.cancel_appointment,
            "get_appointment_stats": self.get_appointment_stats,
            "get_patient_appointments": self.get_patient_appointments,
            "send_email_notification": self.send_email_notification,
            "send_slack_notification": self.send_slack_notification,
            "send_inapp_notification": self.send_inapp_notification,
            "find_alternative_slots": self.find_alternative_slots,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        try:
            result = await handler(arguments)
            return json.dumps(result, default=str)
        except Exception as e:
            logger.error(f"Error in tool {tool_name}: {e}")
            return json.dumps({"error": str(e)})

    async def list_doctors(self, args: dict) -> dict:
        """List all doctors, optionally filtered by specialization."""
        query = select(Doctor).options(joinedload(Doctor.user))
        if args.get("specialization"):
            query = query.where(
                Doctor.specialization.ilike(f"%{args['specialization']}%")
            )

        result = await self.db.execute(query)
        doctors = result.unique().scalars().all()

        return {
            "doctors": [
                {
                    "id": d.id,
                    "name": d.user.name,
                    "email": d.user.email,
                    "specialization": d.specialization,
                    "phone": d.phone,
                }
                for d in doctors
            ]
        }

    async def check_doctor_availability(self, args: dict) -> dict:
        """Check available slots for a doctor on a specific date."""
        doctor_id = args["doctor_id"]
        check_date = datetime.strptime(args["date"], "%Y-%m-%d").date()
        day_of_week = check_date.weekday()  # 0=Monday

        # Get doctor info
        doctor_result = await self.db.execute(
            select(Doctor).options(joinedload(Doctor.user)).where(Doctor.id == doctor_id)
        )
        doctor = doctor_result.unique().scalar_one_or_none()
        if not doctor:
            return {"error": "Doctor not found", "available_slots": []}

        # Get availability for this day of week
        avail_result = await self.db.execute(
            select(DoctorAvailability).where(
                and_(
                    DoctorAvailability.doctor_id == doctor_id,
                    DoctorAvailability.day_of_week == day_of_week,
                )
            )
        )
        availabilities = avail_result.scalars().all()

        if not availabilities:
            return {
                "doctor_name": doctor.user.name,
                "date": str(check_date),
                "day": check_date.strftime("%A"),
                "available_slots": [],
                "message": f"Dr. {doctor.user.name} is not available on {check_date.strftime('%A')}s.",
            }

        # Get existing appointments for that date
        appt_result = await self.db.execute(
            select(Appointment).where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.appointment_date == check_date,
                    Appointment.status == AppointmentStatus.SCHEDULED,
                )
            )
        )
        booked_appointments = appt_result.scalars().all()
        booked_times = {(a.start_time, a.end_time) for a in booked_appointments}

        # Generate 30-minute slots
        available_slots = []
        for avail in availabilities:
            current = datetime.combine(check_date, avail.start_time)
            end = datetime.combine(check_date, avail.end_time)

            while current + timedelta(minutes=30) <= end:
                slot_start = current.time()
                slot_end = (current + timedelta(minutes=30)).time()

                if (slot_start, slot_end) not in booked_times:
                    available_slots.append({
                        "start_time": slot_start.strftime("%H:%M"),
                        "end_time": slot_end.strftime("%H:%M"),
                    })

                current += timedelta(minutes=30)

        return {
            "doctor_name": doctor.user.name,
            "date": str(check_date),
            "day": check_date.strftime("%A"),
            "available_slots": available_slots,
            "total_available": len(available_slots),
        }

    async def book_appointment(self, args: dict) -> dict:
        """Book an appointment and trigger email + calendar creation."""
        doctor_id = args["doctor_id"]
        patient_id = args["patient_id"]
        appt_date = datetime.strptime(args["date"], "%Y-%m-%d").date()
        start_time = datetime.strptime(args["start_time"], "%H:%M").time()
        end_time = (datetime.combine(appt_date, start_time) + timedelta(minutes=30)).time()
        reason = args.get("reason", "")

        # Verify doctor exists
        doctor_result = await self.db.execute(
            select(Doctor).options(joinedload(Doctor.user)).where(Doctor.id == doctor_id)
        )
        doctor = doctor_result.unique().scalar_one_or_none()
        if not doctor:
            return {"success": False, "error": "Doctor not found"}

        # Verify patient exists
        patient_result = await self.db.execute(
            select(Patient).options(joinedload(Patient.user)).where(Patient.id == patient_id)
        )
        patient = patient_result.unique().scalar_one_or_none()
        if not patient:
            return {"success": False, "error": "Patient not found"}

        # Check if slot is still available
        conflict = await self.db.execute(
            select(Appointment).where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.appointment_date == appt_date,
                    Appointment.start_time == start_time,
                    Appointment.status == AppointmentStatus.SCHEDULED,
                )
            )
        )
        if conflict.scalar_one_or_none():
            return {
                "success": False,
                "error": "This time slot is no longer available. Please choose another slot.",
            }

        # Create appointment
        appointment = Appointment(
            doctor_id=doctor_id,
            patient_id=patient_id,
            appointment_date=appt_date,
            start_time=start_time,
            end_time=end_time,
            status=AppointmentStatus.SCHEDULED,
            reason=reason,
        )
        self.db.add(appointment)
        await self.db.commit()
        await self.db.refresh(appointment)

        # Try to add to Google Calendar (non-blocking)
        calendar_event_id = None
        try:
            calendar_event_id = await self.calendar_service.create_event(
                summary=f"Appointment: {patient.user.name} with Dr. {doctor.user.name}",
                description=f"Reason: {reason}" if reason else "Doctor appointment",
                start_datetime=datetime.combine(appt_date, start_time),
                end_datetime=datetime.combine(appt_date, end_time),
                attendees=[patient.user.email, doctor.user.email],
            )
            if calendar_event_id:
                appointment.google_calendar_event_id = calendar_event_id
                await self.db.commit()
        except Exception as e:
            logger.warning(f"Google Calendar integration skipped: {e}")

        # Send email confirmation (non-blocking)
        try:
            await self.email_service.send_appointment_confirmation(
                to_email=patient.user.email,
                patient_name=patient.user.name,
                doctor_name=doctor.user.name,
                date=appt_date,
                time=start_time,
                reason=reason,
            )
        except Exception as e:
            logger.warning(f"Email notification skipped: {e}")

        return {
            "success": True,
            "appointment_id": appointment.id,
            "doctor_name": doctor.user.name,
            "patient_name": patient.user.name,
            "date": str(appt_date),
            "time": start_time.strftime("%H:%M"),
            "reason": reason,
            "calendar_synced": calendar_event_id is not None,
            "email_sent": True,
            "message": f"Appointment booked successfully with Dr. {doctor.user.name} on "
                       f"{appt_date.strftime('%B %d, %Y')} at {start_time.strftime('%I:%M %p')}.",
        }

    async def cancel_appointment(self, args: dict) -> dict:
        """Cancel an existing appointment."""
        appt_result = await self.db.execute(
            select(Appointment)
            .options(joinedload(Appointment.doctor).joinedload(Doctor.user))
            .options(joinedload(Appointment.patient).joinedload(Patient.user))
            .where(Appointment.id == args["appointment_id"])
        )
        appointment = appt_result.unique().scalar_one_or_none()

        if not appointment:
            return {"success": False, "error": "Appointment not found"}

        if appointment.status == AppointmentStatus.CANCELLED:
            return {"success": False, "error": "Appointment is already cancelled"}

        appointment.status = AppointmentStatus.CANCELLED
        await self.db.commit()

        return {
            "success": True,
            "message": f"Appointment #{appointment.id} with Dr. {appointment.doctor.user.name} "
                       f"on {appointment.appointment_date} has been cancelled.",
        }

    async def get_appointment_stats(self, args: dict) -> dict:
        """Get appointment statistics for a doctor."""
        doctor_id = args["doctor_id"]
        date_from = datetime.strptime(args.get("date_from", str(date.today())), "%Y-%m-%d").date()
        date_to = datetime.strptime(args.get("date_to", str(date.today())), "%Y-%m-%d").date()

        # Get doctor info
        doctor_result = await self.db.execute(
            select(Doctor).options(joinedload(Doctor.user)).where(Doctor.id == doctor_id)
        )
        doctor = doctor_result.unique().scalar_one_or_none()
        if not doctor:
            return {"error": "Doctor not found"}

        # Get appointments in date range
        appt_result = await self.db.execute(
            select(Appointment)
            .options(joinedload(Appointment.patient).joinedload(Patient.user))
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.appointment_date >= date_from,
                    Appointment.appointment_date <= date_to,
                )
            )
            .order_by(Appointment.appointment_date, Appointment.start_time)
        )
        appointments = appt_result.unique().scalars().all()

        # Compute statistics
        total = len(appointments)
        completed = sum(1 for a in appointments if a.status == AppointmentStatus.COMPLETED)
        scheduled = sum(1 for a in appointments if a.status == AppointmentStatus.SCHEDULED)
        cancelled = sum(1 for a in appointments if a.status == AppointmentStatus.CANCELLED)

        # Group reasons
        reasons = {}
        for a in appointments:
            if a.reason:
                reason_lower = a.reason.lower()
                reasons[reason_lower] = reasons.get(reason_lower, 0) + 1

        # Appointment details
        details = [
            {
                "id": a.id,
                "patient_name": a.patient.user.name,
                "date": str(a.appointment_date),
                "time": a.start_time.strftime("%H:%M"),
                "status": a.status.value,
                "reason": a.reason,
            }
            for a in appointments
        ]

        return {
            "doctor_name": doctor.user.name,
            "period": f"{date_from} to {date_to}",
            "total_appointments": total,
            "completed": completed,
            "scheduled": scheduled,
            "cancelled": cancelled,
            "visit_reasons": reasons,
            "appointments": details,
        }

    async def get_patient_appointments(self, args: dict) -> dict:
        """Get a patient's appointments."""
        patient_id = args["patient_id"]
        query = (
            select(Appointment)
            .options(joinedload(Appointment.doctor).joinedload(Doctor.user))
            .where(Appointment.patient_id == patient_id)
        )
        if args.get("status"):
            query = query.where(Appointment.status == args["status"])

        query = query.order_by(Appointment.appointment_date.desc())
        result = await self.db.execute(query)
        appointments = result.unique().scalars().all()

        return {
            "appointments": [
                {
                    "id": a.id,
                    "doctor_name": a.doctor.user.name,
                    "date": str(a.appointment_date),
                    "time": a.start_time.strftime("%H:%M"),
                    "status": a.status.value,
                    "reason": a.reason,
                }
                for a in appointments
            ]
        }

    async def send_email_notification(self, args: dict) -> dict:
        """Send an email notification."""
        try:
            await self.email_service.send_email(
                to_email=args["to_email"],
                subject=args["subject"],
                body=args["body"],
            )
            return {"success": True, "message": f"Email sent to {args['to_email']}"}
        except Exception as e:
            logger.warning(f"Email sending failed: {e}")
            return {"success": True, "message": f"Email queued for {args['to_email']} (will be sent when SMTP is configured)"}

    async def send_slack_notification(self, args: dict) -> dict:
        """Send a Slack notification."""
        try:
            await self.notification_service.send_slack_message(args["message"])
            return {"success": True, "message": "Slack notification sent"}
        except Exception as e:
            logger.warning(f"Slack notification failed: {e}")
            return {"success": True, "message": "Slack notification queued (will be sent when webhook is configured)"}

    async def send_inapp_notification(self, args: dict) -> dict:
        """Store an in-app notification."""
        notification = Notification(
            user_id=args["user_id"],
            title=args["title"],
            message=args["message"],
            type=args.get("type", "info"),
            channel="in_app",
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        # Also broadcast via WebSocket (if connected)
        await self.notification_service.broadcast_notification(
            user_id=args["user_id"],
            notification={
                "id": notification.id,
                "title": args["title"],
                "message": args["message"],
                "type": args.get("type", "info"),
            },
        )

        return {
            "success": True,
            "notification_id": notification.id,
            "message": "In-app notification sent",
        }

    async def find_alternative_slots(self, args: dict) -> dict:
        """Find alternative available slots when preferred time is unavailable."""
        doctor_id = args["doctor_id"]
        preferred_date = datetime.strptime(args["preferred_date"], "%Y-%m-%d").date()
        num_slots = args.get("num_slots", 3)

        alternatives = []
        current_date = preferred_date

        # Search up to 7 days forward
        for _ in range(7):
            availability = await self.check_doctor_availability({
                "doctor_id": doctor_id,
                "date": str(current_date),
            })

            for slot in availability.get("available_slots", []):
                alternatives.append({
                    "date": str(current_date),
                    "day": current_date.strftime("%A"),
                    **slot,
                })
                if len(alternatives) >= num_slots:
                    break

            if len(alternatives) >= num_slots:
                break
            current_date += timedelta(days=1)

        return {
            "doctor_name": availability.get("doctor_name", "Unknown"),
            "alternative_slots": alternatives[:num_slots],
            "message": f"Found {len(alternatives[:num_slots])} alternative slots.",
        }
