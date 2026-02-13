"""
LLM Agent with MCP Tool Integration.

This is the core agentic component that:
1. Receives natural language input from users
2. Maintains conversation context across multiple turns
3. Dynamically decides which MCP tools to invoke
4. Orchestrates multi-step workflows (check availability -> book -> notify)
5. Returns human-readable responses

Supports both OpenAI and Anthropic LLMs with function/tool calling.
"""

import json
import logging
from datetime import datetime, date
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.mcp_server.tool_handlers import ToolHandlers

logger = logging.getLogger(__name__)

# System prompt that defines the agent's behavior and available tools
SYSTEM_PROMPT = """You are a smart medical appointment assistant. You help patients book appointments with doctors and help doctors view their schedules and reports.

You have access to the following tools via MCP (Model Context Protocol):

1. **list_doctors** - List available doctors and their specializations
2. **check_doctor_availability** - Check a doctor's available time slots for a date
3. **book_appointment** - Book an appointment (creates DB record + Google Calendar event + email confirmation)
4. **cancel_appointment** - Cancel an existing appointment
5. **get_appointment_stats** - Get appointment statistics/summary for a doctor
6. **get_patient_appointments** - View a patient's appointments
7. **send_email_notification** - Send email to a user
8. **send_slack_notification** - Send Slack message (for doctor reports)
9. **send_inapp_notification** - Send in-app notification
10. **find_alternative_slots** - Find alternative slots when preferred time is unavailable

**Important behavioral rules:**
- When a patient wants to book, ALWAYS check availability first before booking.
- If the requested slot is unavailable, use find_alternative_slots to suggest alternatives.
- When booking is successful, confirm the details clearly.
- For doctor queries (stats, reports), use get_appointment_stats and summarize the results.
- When sending doctor reports, use Slack or in-app notifications (NOT email - that's for patients).
- Use today's date as reference: {today}.
- Parse relative dates like "tomorrow", "next Monday", "Friday" correctly relative to today.
- Be concise but friendly in responses.
- If you need more information (like which doctor, what date), ask the user.
- Maintain conversation context - remember previously discussed doctors, dates, and preferences.

**Current user context:**
- User Role: {role}
- User ID: {user_id}
- Patient/Doctor ID: {profile_id}
- User Name: {user_name}
"""


def get_tool_definitions() -> list[dict]:
    """Return OpenAI-compatible function definitions for all MCP tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "list_doctors",
                "description": "List all available doctors with their specializations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "specialization": {"type": "string", "description": "Filter by specialization (optional)"}
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_doctor_availability",
                "description": "Check available time slots for a doctor on a specific date.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doctor_id": {"type": "integer", "description": "Doctor's ID"},
                        "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    },
                    "required": ["doctor_id", "date"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": "Book an appointment. Creates DB record, Google Calendar event, and sends email confirmation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doctor_id": {"type": "integer", "description": "Doctor's ID"},
                        "patient_id": {"type": "integer", "description": "Patient's ID"},
                        "date": {"type": "string", "description": "Date in YYYY-MM-DD"},
                        "start_time": {"type": "string", "description": "Start time HH:MM"},
                        "reason": {"type": "string", "description": "Reason for visit"},
                    },
                    "required": ["doctor_id", "patient_id", "date", "start_time"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_appointment",
                "description": "Cancel an existing appointment by ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "appointment_id": {"type": "integer", "description": "Appointment ID"},
                    },
                    "required": ["appointment_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_appointment_stats",
                "description": "Get appointment statistics for a doctor in a date range.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doctor_id": {"type": "integer", "description": "Doctor's ID"},
                        "date_from": {"type": "string", "description": "Start date YYYY-MM-DD (defaults to today)"},
                        "date_to": {"type": "string", "description": "End date YYYY-MM-DD (defaults to today)"},
                    },
                    "required": ["doctor_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_patient_appointments",
                "description": "Get a patient's appointment history.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "integer", "description": "Patient's ID"},
                        "status": {"type": "string", "description": "Filter: scheduled, completed, cancelled"},
                    },
                    "required": ["patient_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "send_email_notification",
                "description": "Send an email notification.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to_email": {"type": "string", "description": "Recipient email"},
                        "subject": {"type": "string", "description": "Subject"},
                        "body": {"type": "string", "description": "Email body (HTML)"},
                    },
                    "required": ["to_email", "subject", "body"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "send_slack_notification",
                "description": "Send a Slack notification (used for doctor reports).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to send"},
                    },
                    "required": ["message"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "send_inapp_notification",
                "description": "Send an in-app notification to a user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer", "description": "User ID"},
                        "title": {"type": "string", "description": "Title"},
                        "message": {"type": "string", "description": "Message"},
                        "type": {"type": "string", "description": "'info', 'success', or 'warning'"},
                    },
                    "required": ["user_id", "title", "message"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "find_alternative_slots",
                "description": "Find alternative available slots when preferred time is unavailable.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doctor_id": {"type": "integer", "description": "Doctor's ID"},
                        "preferred_date": {"type": "string", "description": "Preferred date YYYY-MM-DD"},
                        "num_slots": {"type": "integer", "description": "Number of alternatives (default: 3)"},
                    },
                    "required": ["doctor_id", "preferred_date"],
                },
            },
        },
    ]


class DoctorAppointmentAgent:
    """
    Agentic AI that uses MCP tools to handle doctor appointments.

    The agent maintains conversation history for multi-turn interactions
    and dynamically selects which tools to invoke based on user intent.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tool_handlers = ToolHandlers(db)
        self.settings = get_settings()

    async def process_message(
        self,
        user_message: str,
        conversation_history: list[dict],
        user_context: dict,
    ) -> tuple[str, list[dict], list[str]]:
        """
        Process a user message using the LLM agent.

        Args:
            user_message: The user's natural language input
            conversation_history: Previous messages for context continuity
            user_context: User info (role, id, name, etc.)

        Returns:
            tuple: (agent_response, updated_history, actions_taken)
        """
        actions_taken = []

        # Build system prompt with user context
        system = SYSTEM_PROMPT.format(
            today=date.today().strftime("%Y-%m-%d (%A)"),
            role=user_context.get("role", "patient"),
            user_id=user_context.get("user_id", 0),
            profile_id=user_context.get("profile_id", 0),
            user_name=user_context.get("name", "User"),
        )

        # Add new user message to history
        conversation_history.append({"role": "user", "content": user_message})

        # Use OpenAI or Anthropic based on config
        if self.settings.LLM_PROVIDER == "anthropic" and self.settings.ANTHROPIC_API_KEY:
            response_text, actions_taken = await self._call_anthropic(
                system, conversation_history, actions_taken
            )
        else:
            response_text, actions_taken = await self._call_openai(
                system, conversation_history, actions_taken
            )

        # Add assistant response to history
        conversation_history.append({"role": "assistant", "content": response_text})

        return response_text, conversation_history, actions_taken

    async def _call_openai(
        self, system: str, history: list[dict], actions: list[str]
    ) -> tuple[str, list[str]]:
        """Execute agent loop using OpenAI's function calling."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
        messages = [{"role": "system", "content": system}] + history
        tools = get_tool_definitions()

        # Agent loop: keep calling until no more tool calls
        max_iterations = 10
        for _ in range(max_iterations):
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )

            choice = response.choices[0]

            # If no tool calls, return the response
            if not choice.message.tool_calls:
                return choice.message.content or "I'm sorry, I couldn't process that.", actions

            # Process each tool call
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                logger.info(f"Agent invoking MCP tool: {tool_name}({tool_args})")
                actions.append(f"Called {tool_name}")

                # Execute via MCP tool handler
                result = await self.tool_handlers.handle_tool_call(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        return "I've completed processing your request.", actions

    async def _call_anthropic(
        self, system: str, history: list[dict], actions: list[str]
    ) -> tuple[str, list[str]]:
        """Execute agent loop using Anthropic's tool use."""
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.settings.ANTHROPIC_API_KEY)

        # Convert tool definitions to Anthropic format
        tools = []
        for t in get_tool_definitions():
            tools.append({
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"],
            })

        messages = history.copy()

        max_iterations = 10
        for _ in range(max_iterations):
            response = await client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=system,
                messages=messages,
                tools=tools,
            )

            # Check if there are tool use blocks
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_use_blocks:
                # Extract text response
                text_blocks = [b.text for b in response.content if b.type == "text"]
                return "\n".join(text_blocks) or "Done.", actions

            # Process tool calls
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in tool_use_blocks:
                tool_name = block.name
                tool_args = block.input

                logger.info(f"Agent invoking MCP tool: {tool_name}({tool_args})")
                actions.append(f"Called {tool_name}")

                result = await self.tool_handlers.handle_tool_call(tool_name, tool_args)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

        return "I've completed processing your request.", actions
