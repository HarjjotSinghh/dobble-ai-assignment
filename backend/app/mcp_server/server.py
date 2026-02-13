"""
MCP (Model Context Protocol) Server Implementation.

This server exposes tools, resources, and prompts that allow an LLM agent
to dynamically discover and invoke backend capabilities for:
- Checking doctor availability
- Booking appointments
- Querying appointment statistics
- Sending notifications (email, Slack, in-app)

Architecture:
  MCP Client (LLM Agent) <---> MCP Server <---> FastAPI/DB/External APIs
"""

from datetime import datetime, date, time, timedelta
from typing import Any
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
    Prompt,
    PromptMessage,
    PromptArgument,
)
import json
import logging

logger = logging.getLogger(__name__)

# Create the MCP server instance
mcp_server = Server("doctor-appointment-mcp")


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS - These are dynamically discoverable by the LLM agent
# ═══════════════════════════════════════════════════════════════════════════════

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """Return all available tools the LLM agent can invoke."""
    return [
        Tool(
            name="list_doctors",
            description="List all available doctors with their specializations. Use this when the user wants to know which doctors are available or asks about a specific doctor.",
            inputSchema={
                "type": "object",
                "properties": {
                    "specialization": {
                        "type": "string",
                        "description": "Filter by specialization (e.g., 'General Physician', 'Cardiologist'). Optional.",
                    }
                },
            },
        ),
        Tool(
            name="check_doctor_availability",
            description="Check a doctor's available time slots for a specific date. Returns available 30-minute slots based on the doctor's schedule and existing appointments.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctor_id": {
                        "type": "integer",
                        "description": "The doctor's ID",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date to check availability (YYYY-MM-DD format)",
                    },
                },
                "required": ["doctor_id", "date"],
            },
        ),
        Tool(
            name="book_appointment",
            description="Book an appointment with a doctor. This will create the appointment in the database, optionally add it to Google Calendar, and send an email confirmation to the patient.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctor_id": {
                        "type": "integer",
                        "description": "The doctor's ID",
                    },
                    "patient_id": {
                        "type": "integer",
                        "description": "The patient's ID",
                    },
                    "date": {
                        "type": "string",
                        "description": "Appointment date (YYYY-MM-DD)",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time (HH:MM format, e.g., '09:00')",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the appointment",
                    },
                },
                "required": ["doctor_id", "patient_id", "date", "start_time"],
            },
        ),
        Tool(
            name="cancel_appointment",
            description="Cancel an existing appointment by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "integer",
                        "description": "The appointment ID to cancel",
                    },
                },
                "required": ["appointment_id"],
            },
        ),
        Tool(
            name="get_appointment_stats",
            description="Get appointment statistics for a doctor. Useful for generating summary reports about patient visits, upcoming appointments, and reasons for visits.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctor_id": {
                        "type": "integer",
                        "description": "The doctor's ID",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date for the report (YYYY-MM-DD). Defaults to today.",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date for the report (YYYY-MM-DD). Defaults to today.",
                    },
                },
                "required": ["doctor_id"],
            },
        ),
        Tool(
            name="get_patient_appointments",
            description="Get a patient's appointments (past and upcoming).",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "integer",
                        "description": "The patient's ID",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status: 'scheduled', 'completed', 'cancelled'. Optional.",
                    },
                },
                "required": ["patient_id"],
            },
        ),
        Tool(
            name="send_email_notification",
            description="Send an email notification to a user (patient or doctor).",
            inputSchema={
                "type": "object",
                "properties": {
                    "to_email": {
                        "type": "string",
                        "description": "Recipient email address",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject",
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body content",
                    },
                },
                "required": ["to_email", "subject", "body"],
            },
        ),
        Tool(
            name="send_slack_notification",
            description="Send a notification via Slack webhook. Used for doctor summary reports and alerts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to send to Slack",
                    },
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="send_inapp_notification",
            description="Send an in-app notification to a user. This is stored in the database and delivered via the frontend.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The user ID to notify",
                    },
                    "title": {
                        "type": "string",
                        "description": "Notification title",
                    },
                    "message": {
                        "type": "string",
                        "description": "Notification message",
                    },
                    "type": {
                        "type": "string",
                        "description": "Notification type: 'info', 'success', 'warning'",
                    },
                },
                "required": ["user_id", "title", "message"],
            },
        ),
        Tool(
            name="find_alternative_slots",
            description="When a requested slot is unavailable, find the next available slots for the doctor. Supports auto-rescheduling.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doctor_id": {
                        "type": "integer",
                        "description": "The doctor's ID",
                    },
                    "preferred_date": {
                        "type": "string",
                        "description": "The preferred date (YYYY-MM-DD). Will search from this date forward.",
                    },
                    "num_slots": {
                        "type": "integer",
                        "description": "Number of alternative slots to return (default: 3)",
                    },
                },
                "required": ["doctor_id", "preferred_date"],
            },
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCE DEFINITIONS - Expose data sources via MCP
# ═══════════════════════════════════════════════════════════════════════════════

@mcp_server.list_resources()
async def list_resources() -> list[Resource]:
    """List available MCP resources."""
    return [
        Resource(
            uri="doctor://list",
            name="Doctor Directory",
            description="List of all doctors and their specializations",
            mimeType="application/json",
        ),
        Resource(
            uri="appointment://today",
            name="Today's Appointments",
            description="All appointments scheduled for today",
            mimeType="application/json",
        ),
    ]


@mcp_server.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    """List available resource templates for dynamic data."""
    return [
        ResourceTemplate(
            uriTemplate="doctor://{doctor_id}/schedule/{date}",
            name="Doctor Schedule",
            description="Get a specific doctor's schedule for a given date",
            mimeType="application/json",
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT DEFINITIONS - Pre-built prompt templates for common tasks
# ═══════════════════════════════════════════════════════════════════════════════

@mcp_server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompt templates."""
    return [
        Prompt(
            name="book_appointment",
            description="Help a patient book an appointment with a doctor",
            arguments=[
                PromptArgument(
                    name="doctor_name",
                    description="Name of the doctor",
                    required=True,
                ),
                PromptArgument(
                    name="preferred_time",
                    description="Preferred date and time",
                    required=True,
                ),
            ],
        ),
        Prompt(
            name="doctor_daily_summary",
            description="Generate a daily summary report for a doctor",
            arguments=[
                PromptArgument(
                    name="doctor_name",
                    description="Name of the doctor",
                    required=True,
                ),
            ],
        ),
    ]


@mcp_server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> list[PromptMessage]:
    """Return prompt messages for a given prompt template."""
    if name == "book_appointment":
        return [
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=f"I want to book an appointment with {arguments.get('doctor_name', 'a doctor')} "
                         f"at {arguments.get('preferred_time', 'the earliest available time')}. "
                         f"Please check availability and book it for me.",
                ),
            )
        ]
    elif name == "doctor_daily_summary":
        return [
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=f"Generate a comprehensive daily summary report for {arguments.get('doctor_name', 'the doctor')}. "
                         f"Include: number of appointments today, patient details, reasons for visits, "
                         f"and any completed appointments from yesterday.",
                ),
            )
        ]
    return []
