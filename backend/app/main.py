"""
FastAPI Application Entry Point with MCP Lifecycle Management.

This is the HOST layer in the MCP architecture that:
1. Manages the MCP client-server lifecycle (startup/shutdown)
2. Serves the REST API endpoints (auth, chat, appointments, notifications)
3. Initializes the database and seeds demo data
4. Configures CORS for the React frontend

Architecture:
  ┌─────────────────────────────────────────────────────────┐
  │  HOST APPLICATION (this file)                           │
  │                                                         │
  │  ┌─────────────────────────────────────────────────┐    │
  │  │  MCP Client (app.state.mcp_client)              │    │
  │  │  - Spawns MCP Server as subprocess              │    │
  │  │  - Maintains persistent stdio connection        │    │
  │  │  - Provides dynamic tool discovery              │    │
  │  └──────────────────┬──────────────────────────────┘    │
  │                     │ stdio transport (JSON-RPC 2.0)    │
  │  ┌──────────────────▼──────────────────────────────┐    │
  │  │  MCP Server (subprocess)                        │    │
  │  │  mcp_server/server.py                           │    │
  │  │  - 10 tools, 2 resources, 2 prompts             │    │
  │  │  - Own database connection pool                 │    │
  │  │  - External service integrations                │    │
  │  └─────────────────────────────────────────────────┘    │
  │                                                         │
  │  Routers: auth, chat, appointments, notifications       │
  │  Database: PostgreSQL (async via SQLAlchemy)             │
  └─────────────────────────────────────────────────────────┘
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, async_session
from app.routers import auth, chat, appointments, notifications
from app.mcp_client.client import MCPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.

    On startup:
      1. Initialize database tables
      2. Seed demo data
      3. Start MCP server subprocess and connect MCP client
      4. Store MCP client in app.state for request handlers

    On shutdown:
      1. Disconnect MCP client (terminates server subprocess)
    """
    logger.info("Starting Doctor Appointment MCP Application...")

    # Step 1: Initialize database tables
    await init_db()
    logger.info("Database tables created/verified")

    # Step 2: Seed demo data
    await seed_demo_data()

    # Step 3: Start MCP client-server connection
    mcp_client = MCPClient()
    try:
        await mcp_client.connect()
        app.state.mcp_client = mcp_client

        # Log discovered capabilities
        capabilities = await mcp_client.get_server_capabilities()
        logger.info(
            f"MCP Server ready - "
            f"Tools: {capabilities['tool_count']}, "
            f"Resources: {capabilities['resource_count']}, "
            f"Prompts: {capabilities['prompt_count']}"
        )
        logger.info(f"Available MCP tools: {capabilities['tools']}")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        logger.warning("Application will start without MCP - chat features unavailable")
        app.state.mcp_client = None

    yield

    # Shutdown: disconnect MCP client and terminate server subprocess
    logger.info("Shutting down...")
    if hasattr(app.state, "mcp_client") and app.state.mcp_client:
        await app.state.mcp_client.disconnect()
        logger.info("MCP Client disconnected, server subprocess terminated")


app = FastAPI(
    title="Doctor Appointment Assistant - MCP Architecture",
    description=(
        "A smart doctor appointment and reporting assistant built with "
        "true MCP (Model Context Protocol) architecture. The LLM agent "
        "discovers tools dynamically from the MCP server via the protocol "
        "and routes all tool calls through the MCP client-server channel."
    ),
    version="2.0.0",
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
    """
    Health check endpoint.

    Returns MCP server status including dynamically discovered tools.
    Tools are NOT hardcoded here - they are queried from the MCP client
    which discovered them from the MCP server via the protocol.
    """
    mcp_client = getattr(app.state, "mcp_client", None)

    if mcp_client and mcp_client.is_connected:
        capabilities = await mcp_client.get_server_capabilities()
        return {
            "status": "healthy",
            "service": "Doctor Appointment MCP Application",
            "version": "2.0.0",
            "mcp": {
                "connected": True,
                "tools": capabilities["tools"],
                "tool_count": capabilities["tool_count"],
                "resources": capabilities["resources"],
                "prompts": capabilities["prompts"],
            },
        }
    else:
        return {
            "status": "degraded",
            "service": "Doctor Appointment MCP Application",
            "version": "2.0.0",
            "mcp": {"connected": False},
        }


@app.get("/api/health")
async def health():
    """Detailed health check including MCP server status."""
    mcp_client = getattr(app.state, "mcp_client", None)
    mcp_status = "connected" if (mcp_client and mcp_client.is_connected) else "disconnected"

    return {
        "status": "ok",
        "mcp_server": mcp_status,
    }


async def seed_demo_data():
    """Seed demo data if the database is empty."""
    from sqlalchemy import select
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
