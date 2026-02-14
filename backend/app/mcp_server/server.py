"""
MCP Server - Standalone Model Context Protocol Server.

This is a proper MCP server that exposes tools, resources, and prompts
through the standardized MCP protocol. It runs as an independent process
and communicates with the MCP client via stdio transport.

Architecture (MCP Design Pattern):
  ┌──────────────────────────────────────────┐
  │  HOST (FastAPI Application)              │
  │  ┌────────────────────────────────────┐  │
  │  │  MCP Client (mcp_client/client.py) │  │
  │  └──────────┬─────────────────────────┘  │
  └─────────────┼────────────────────────────┘
                │  stdio transport (JSON-RPC 2.0)
  ┌─────────────▼────────────────────────────┐
  │  MCP Server (this file)                  │
  │  ├── Tools (10 medical appointment tools)│
  │  ├── Resources (doctor directory, etc.)  │
  │  ├── Prompts (booking, reports)          │
  │  └── Database + External Services        │
  └──────────────────────────────────────────┘

The server dynamically exposes capabilities that the MCP client
discovers at runtime via the protocol's tools/list, resources/list,
and prompts/list methods - NOT hardcoded in the agent.
"""

import sys
import os
import json
import logging
import asyncio
from datetime import datetime, date, time, timedelta
from typing import Any, Optional
from pathlib import Path

# Ensure the backend directory is on the Python path so we can import app modules
# when this script runs as a subprocess
_backend_dir = str(Path(__file__).resolve().parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# MCP SERVER INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

mcp = FastMCP(
    "doctor-appointment-mcp",
    instructions=(
        "MCP server for a doctor appointment scheduling system. "
        "Provides tools for listing doctors, checking availability, "
        "booking/cancelling appointments, generating reports, and "
        "sending multi-channel notifications."
    ),
)


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE SESSION FACTORY (for standalone subprocess execution)
# ═══════════════════════════════════════════════════════════════════════════════

_engine = None
_async_session_factory = None


async def _get_db_session():
    """Create a database session for tool execution.

    The MCP server runs as an independent process, so it manages
    its own database connections separate from the FastAPI host.
    """
    global _engine, _async_session_factory

    if _engine is None:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
        from app.config import get_settings

        settings = get_settings()
        _engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
        _async_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    return _async_session_factory()


def _get_tool_handlers():
    """Lazy import to avoid circular dependencies at module level."""
    from app.mcp_server.tool_handlers import ToolHandlers
    return ToolHandlers


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS - Dynamically discoverable via MCP tools/list protocol
#
# Each tool is registered with the MCP server using @mcp.tool() decorator.
# The MCP client discovers these at runtime by calling session.list_tools().
# Tool schemas (name, description, input_schema) are auto-generated from
# the function signatures and docstrings.
# ═══════════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def list_doctors(specialization: str = "") -> str:
    """List all available doctors with their specializations.
    Use this when the user wants to know which doctors are available
    or asks about a specific specialization.

    Args:
        specialization: Filter by specialization (e.g., 'General Physician', 'Cardiologist'). Optional.
    """
    db = await _get_db_session()
    try:
        handlers = _get_tool_handlers()(db)
        result = await handlers.list_doctors({"specialization": specialization or None})
        return json.dumps(result, default=str)
    finally:
        await db.close()


@mcp.tool()
async def check_doctor_availability(doctor_id: int, date: str) -> str:
    """Check a doctor's available time slots for a specific date.
    Returns available 30-minute slots based on the doctor's schedule
    and existing appointments.

    Args:
        doctor_id: The doctor's ID
        date: Date to check availability (YYYY-MM-DD format)
    """
    db = await _get_db_session()
    try:
        handlers = _get_tool_handlers()(db)
        result = await handlers.check_doctor_availability({
            "doctor_id": doctor_id,
            "date": date,
        })
        return json.dumps(result, default=str)
    finally:
        await db.close()


@mcp.tool()
async def book_appointment(
    doctor_id: int,
    patient_id: int,
    date: str,
    start_time: str,
    reason: str = "",
) -> str:
    """Book an appointment with a doctor. This creates the appointment
    in the database, optionally adds it to Google Calendar, and sends
    an email confirmation to the patient.

    Args:
        doctor_id: The doctor's ID
        patient_id: The patient's ID
        date: Appointment date (YYYY-MM-DD)
        start_time: Start time (HH:MM format, e.g., '09:00')
        reason: Reason for the appointment (optional)
    """
    db = await _get_db_session()
    try:
        handlers = _get_tool_handlers()(db)
        result = await handlers.book_appointment({
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "date": date,
            "start_time": start_time,
            "reason": reason,
        })
        return json.dumps(result, default=str)
    finally:
        await db.close()


@mcp.tool()
async def cancel_appointment(appointment_id: int) -> str:
    """Cancel an existing appointment by its ID.

    Args:
        appointment_id: The appointment ID to cancel
    """
    db = await _get_db_session()
    try:
        handlers = _get_tool_handlers()(db)
        result = await handlers.cancel_appointment({
            "appointment_id": appointment_id,
        })
        return json.dumps(result, default=str)
    finally:
        await db.close()


@mcp.tool()
async def get_appointment_stats(
    doctor_id: int,
    date_from: str = "",
    date_to: str = "",
) -> str:
    """Get appointment statistics for a doctor. Useful for generating
    summary reports about patient visits, upcoming appointments,
    and reasons for visits.

    Args:
        doctor_id: The doctor's ID
        date_from: Start date for the report (YYYY-MM-DD). Defaults to today.
        date_to: End date for the report (YYYY-MM-DD). Defaults to today.
    """
    db = await _get_db_session()
    try:
        handlers = _get_tool_handlers()(db)
        args = {"doctor_id": doctor_id}
        if date_from:
            args["date_from"] = date_from
        if date_to:
            args["date_to"] = date_to
        result = await handlers.get_appointment_stats(args)
        return json.dumps(result, default=str)
    finally:
        await db.close()


@mcp.tool()
async def get_patient_appointments(
    patient_id: int,
    status: str = "",
) -> str:
    """Get a patient's appointments (past and upcoming).

    Args:
        patient_id: The patient's ID
        status: Filter by status: 'scheduled', 'completed', 'cancelled'. Optional.
    """
    db = await _get_db_session()
    try:
        handlers = _get_tool_handlers()(db)
        args = {"patient_id": patient_id}
        if status:
            args["status"] = status
        result = await handlers.get_patient_appointments(args)
        return json.dumps(result, default=str)
    finally:
        await db.close()


@mcp.tool()
async def send_email_notification(
    to_email: str,
    subject: str,
    body: str,
) -> str:
    """Send an email notification to a user (patient or doctor).

    Args:
        to_email: Recipient email address
        subject: Email subject line
        body: Email body content (supports HTML)
    """
    db = await _get_db_session()
    try:
        handlers = _get_tool_handlers()(db)
        result = await handlers.send_email_notification({
            "to_email": to_email,
            "subject": subject,
            "body": body,
        })
        return json.dumps(result, default=str)
    finally:
        await db.close()


@mcp.tool()
async def send_slack_notification(message: str) -> str:
    """Send a notification via Slack webhook. Used for doctor summary
    reports and operational alerts.

    Args:
        message: The message to send to Slack
    """
    db = await _get_db_session()
    try:
        handlers = _get_tool_handlers()(db)
        result = await handlers.send_slack_notification({"message": message})
        return json.dumps(result, default=str)
    finally:
        await db.close()


@mcp.tool()
async def send_inapp_notification(
    user_id: int,
    title: str,
    message: str,
    type: str = "info",
) -> str:
    """Send an in-app notification to a user. This is stored in the
    database and delivered via WebSocket to the frontend in real time.

    Args:
        user_id: The user ID to notify
        title: Notification title
        message: Notification message
        type: Notification type: 'info', 'success', or 'warning'
    """
    db = await _get_db_session()
    try:
        handlers = _get_tool_handlers()(db)
        result = await handlers.send_inapp_notification({
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": type,
        })
        return json.dumps(result, default=str)
    finally:
        await db.close()


@mcp.tool()
async def find_alternative_slots(
    doctor_id: int,
    preferred_date: str,
    num_slots: int = 3,
) -> str:
    """When a requested slot is unavailable, find the next available
    slots for the doctor. Supports auto-rescheduling by searching
    up to 7 days forward from the preferred date.

    Args:
        doctor_id: The doctor's ID
        preferred_date: The preferred date (YYYY-MM-DD). Will search from this date forward.
        num_slots: Number of alternative slots to return (default: 3)
    """
    db = await _get_db_session()
    try:
        handlers = _get_tool_handlers()(db)
        result = await handlers.find_alternative_slots({
            "doctor_id": doctor_id,
            "preferred_date": preferred_date,
            "num_slots": num_slots,
        })
        return json.dumps(result, default=str)
    finally:
        await db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCE DEFINITIONS - Data sources exposed via MCP resources/list
# ═══════════════════════════════════════════════════════════════════════════════


@mcp.resource("doctor://list")
async def get_doctor_list() -> str:
    """List of all doctors and their specializations."""
    db = await _get_db_session()
    try:
        handlers = _get_tool_handlers()(db)
        result = await handlers.list_doctors({})
        return json.dumps(result, default=str)
    finally:
        await db.close()


@mcp.resource("doctor://{doctor_id}/schedule/{schedule_date}")
async def get_doctor_schedule(doctor_id: str, schedule_date: str) -> str:
    """Get a specific doctor's schedule for a given date."""
    db = await _get_db_session()
    try:
        handlers = _get_tool_handlers()(db)
        result = await handlers.check_doctor_availability({
            "doctor_id": int(doctor_id),
            "date": schedule_date,
        })
        return json.dumps(result, default=str)
    finally:
        await db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT TEMPLATES - Pre-built prompt templates discoverable via prompts/list
# ═══════════════════════════════════════════════════════════════════════════════


@mcp.prompt()
def book_appointment_prompt(doctor_name: str, preferred_time: str) -> str:
    """Help a patient book an appointment with a doctor.

    Args:
        doctor_name: Name of the doctor
        preferred_time: Preferred date and time
    """
    return (
        f"I want to book an appointment with {doctor_name} "
        f"at {preferred_time}. Please check availability and book it for me."
    )


@mcp.prompt()
def doctor_daily_summary_prompt(doctor_name: str) -> str:
    """Generate a daily summary report for a doctor.

    Args:
        doctor_name: Name of the doctor
    """
    return (
        f"Generate a comprehensive daily summary report for {doctor_name}. "
        f"Include: number of appointments today, patient details, reasons for visits, "
        f"and any completed appointments from yesterday."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE ENTRY POINT
#
# When run directly (python -m app.mcp_server.server or python server.py),
# the MCP server starts with stdio transport for protocol communication.
# The MCP client spawns this as a subprocess and connects via stdin/stdout.
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("Starting MCP Server (doctor-appointment-mcp) with stdio transport...")
    mcp.run(transport="stdio")
