"""
FastAPI Application Entry Point.

This is the main server that:
1. Serves the REST API endpoints (auth, chat, appointments, notifications)
2. Initializes the database and seeds demo data
3. Configures CORS for the React frontend
4. Provides health check and WebSocket support

Architecture:
  React Frontend <--HTTP/WS--> FastAPI <--MCP Tools--> LLM Agent
                                  |                        |
                              PostgreSQL            External APIs
                                                  (Calendar, Email, Slack)
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, async_session
from app.routers import auth, chat, appointments, notifications

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("Starting Doctor Appointment MCP Server...")

    # Initialize database tables
    await init_db()
    logger.info("Database tables created/verified")

    # Seed demo data
    await seed_demo_data()

    yield

    logger.info("Shutting down...")


app = FastAPI(
    title="Doctor Appointment Assistant - MCP Server",
    description=(
        "A smart doctor appointment and reporting assistant that uses "
        "MCP (Model Context Protocol) to expose APIs and tools dynamically "
        "discovered and invoked by an AI agent."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for React frontend
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(appointments.router)
app.include_router(notifications.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Doctor Appointment MCP Server",
        "version": "1.0.0",
        "mcp_tools": [
            "list_doctors", "check_doctor_availability", "book_appointment",
            "cancel_appointment", "get_appointment_stats", "get_patient_appointments",
            "send_email_notification", "send_slack_notification",
            "send_inapp_notification", "find_alternative_slots",
        ],
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}


async def seed_demo_data():
    """Seed demo data if the database is empty."""
    from sqlalchemy import select, text
    from app.models.models import User, Doctor, Patient, DoctorAvailability, Appointment, AppointmentStatus
    from passlib.context import CryptContext
    from datetime import date, time, datetime, timedelta

    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

    async with async_session() as db:
        # Check if users already exist
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            logger.info("Database already seeded")
            return

        logger.info("Seeding demo data...")

        password_hash = pwd_context.hash("password123")

        # Create demo users
        users = [
            User(email="dr.ahuja@hospital.com", password_hash=password_hash, name="Dr. Priya Ahuja", role="doctor"),
            User(email="dr.sharma@hospital.com", password_hash=password_hash, name="Dr. Rahul Sharma", role="doctor"),
            User(email="dr.patel@hospital.com", password_hash=password_hash, name="Dr. Anita Patel", role="doctor"),
            User(email="john@email.com", password_hash=password_hash, name="John Doe", role="patient"),
            User(email="jane@email.com", password_hash=password_hash, name="Jane Smith", role="patient"),
        ]
        for u in users:
            db.add(u)
        await db.commit()

        for u in users:
            await db.refresh(u)

        # Create doctor profiles
        doctors = [
            Doctor(user_id=users[0].id, specialization="General Physician", phone="+91-9876543210",
                   bio="Experienced general physician with 10+ years of practice."),
            Doctor(user_id=users[1].id, specialization="Cardiologist", phone="+91-9876543211",
                   bio="Heart specialist with expertise in interventional cardiology."),
            Doctor(user_id=users[2].id, specialization="Dermatologist", phone="+91-9876543212",
                   bio="Skin care expert specializing in cosmetic dermatology."),
        ]
        for d in doctors:
            db.add(d)
        await db.commit()

        for d in doctors:
            await db.refresh(d)

        # Create patient profiles
        patients = [
            Patient(user_id=users[3].id, phone="+91-9876543213", date_of_birth=date(1990, 5, 15)),
            Patient(user_id=users[4].id, phone="+91-9876543214", date_of_birth=date(1985, 8, 22)),
        ]
        for p in patients:
            db.add(p)
        await db.commit()

        for p in patients:
            await db.refresh(p)

        # Doctor availability (Monday-Friday)
        for day in range(5):  # Mon-Fri
            db.add(DoctorAvailability(doctor_id=doctors[0].id, day_of_week=day,
                                      start_time=time(9, 0), end_time=time(12, 0)))
            db.add(DoctorAvailability(doctor_id=doctors[0].id, day_of_week=day,
                                      start_time=time(14, 0), end_time=time(17, 0)))

        for day in [0, 2, 4]:  # Mon, Wed, Fri
            db.add(DoctorAvailability(doctor_id=doctors[1].id, day_of_week=day,
                                      start_time=time(10, 0), end_time=time(13, 0)))
            db.add(DoctorAvailability(doctor_id=doctors[1].id, day_of_week=day,
                                      start_time=time(15, 0), end_time=time(18, 0)))

        for day in [1, 3, 5]:  # Tue, Thu, Sat
            db.add(DoctorAvailability(doctor_id=doctors[2].id, day_of_week=day,
                                      start_time=time(9, 0), end_time=time(12, 0)))
            db.add(DoctorAvailability(doctor_id=doctors[2].id, day_of_week=day,
                                      start_time=time(14, 0), end_time=time(16, 0)))

        await db.commit()

        # Create sample appointments
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        tomorrow = today + timedelta(days=1)

        sample_appointments = [
            Appointment(doctor_id=doctors[0].id, patient_id=patients[0].id,
                       appointment_date=yesterday, start_time=time(9, 0), end_time=time(9, 30),
                       status=AppointmentStatus.COMPLETED, reason="Fever and cold"),
            Appointment(doctor_id=doctors[0].id, patient_id=patients[1].id,
                       appointment_date=yesterday, start_time=time(10, 0), end_time=time(10, 30),
                       status=AppointmentStatus.COMPLETED, reason="Regular checkup"),
            Appointment(doctor_id=doctors[0].id, patient_id=patients[0].id,
                       appointment_date=two_days_ago, start_time=time(14, 0), end_time=time(14, 30),
                       status=AppointmentStatus.COMPLETED, reason="Follow-up for fever"),
            Appointment(doctor_id=doctors[1].id, patient_id=patients[0].id,
                       appointment_date=yesterday, start_time=time(10, 0), end_time=time(10, 30),
                       status=AppointmentStatus.COMPLETED, reason="Heart palpitations"),
            Appointment(doctor_id=doctors[0].id, patient_id=patients[1].id,
                       appointment_date=today, start_time=time(9, 0), end_time=time(9, 30),
                       status=AppointmentStatus.SCHEDULED, reason="Headache"),
            Appointment(doctor_id=doctors[0].id, patient_id=patients[0].id,
                       appointment_date=tomorrow, start_time=time(10, 0), end_time=time(10, 30),
                       status=AppointmentStatus.SCHEDULED, reason="Fever follow-up"),
        ]
        for a in sample_appointments:
            db.add(a)
        await db.commit()

        logger.info("Demo data seeded successfully!")
        logger.info("Demo credentials: any user email with password 'password123'")
        logger.info("Patients: john@email.com, jane@email.com")
        logger.info("Doctors: dr.ahuja@hospital.com, dr.sharma@hospital.com, dr.patel@hospital.com")
