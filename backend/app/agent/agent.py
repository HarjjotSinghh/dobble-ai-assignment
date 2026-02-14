"""
LLM Agent with MCP Protocol-Driven Tool Integration.

This is the agentic orchestration layer (HOST component in MCP architecture)
that bridges between the LLM and the MCP protocol:

  1. Discovers available tools DYNAMICALLY from the MCP server via the client
  2. Converts MCP tool schemas to LLM-compatible function definitions
  3. Routes LLM tool calls through the MCP client (protocol-driven)
  4. Maintains multi-turn conversation context via structured sessions
  5. Orchestrates multi-step workflows (check -> book -> notify)

Architecture:
  User Prompt
       │
  ┌────▼────────────────────────────────────────────────────────────────┐
  │  AGENT LOOP (this module)                                           │
  │                                                                     │
  │  1. Query MCP Client → discover_tools() → [tools/list protocol]     │
  │  2. Convert schemas → get_tools_for_llm() → OpenAI/Anthropic fmt    │
  │  3. Send to LLM with tool definitions + conversation history        │
  │  4. LLM decides: call tool(s) or return final answer                │
  │  5. Route tool_call → MCP Client → call_tool() → [tools/call]       │
  │  6. Feed result back to LLM as tool_result                          │
  │  7. Repeat from step 4 until LLM gives final text response          │
  │                                                                     │
  └────┬────────────────────────────────────────────────────────────────┘
       │
  Final Response to User

The agent NEVER directly calls tool handlers. All tool execution flows
through the MCP protocol: Agent → MCP Client → MCP Server → Tool Handler.
"""

import json
import logging
from datetime import date
from typing import Any, Optional

from app.config import get_settings
from app.mcp_client.client import MCPClient

logger = logging.getLogger(__name__)

# System prompt that defines the agent's behavior
# Tool descriptions are NOT listed here - they come dynamically from MCP
SYSTEM_PROMPT = """You are a smart medical appointment assistant. You help patients book appointments with doctors and help doctors view their schedules and reports.

You have access to tools dynamically provided via MCP (Model Context Protocol). Use the tools available to you to fulfill user requests.

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


class DoctorAppointmentAgent:
    """
    Agentic AI orchestrator that uses MCP protocol for tool discovery and execution.

    This agent follows the MCP Host pattern:
    - Tools are NOT hardcoded; they are discovered dynamically from the MCP server
    - Tool calls flow through the MCP client (protocol-driven, not direct calls)
    - The LLM decides which tools to invoke based on discovered capabilities
    - Multi-tool chaining happens naturally through the agent loop
    """

    def __init__(self, mcp_client: MCPClient):
        """
        Initialize the agent with an MCP client connection.

        Args:
            mcp_client: Connected MCP client for tool discovery and invocation.
                        The agent does NOT receive a database session - all data
                        access goes through the MCP protocol.
        """
        self.mcp_client = mcp_client
        self.settings = get_settings()

    async def process_message(
        self,
        user_message: str,
        conversation_history: list[dict],
        user_context: dict,
    ) -> tuple[str, list[dict], list[str]]:
        """
        Process a user message using the LLM agent with MCP tool integration.

        Orchestration flow:
          1. Discover tools from MCP server (dynamic, not static)
          2. Build system prompt with user context
          3. Send to LLM with dynamically-discovered tool schemas
          4. Execute agent loop: LLM → tool_call → MCP Client → result → LLM
          5. Return final response with conversation history and actions taken

        Args:
            user_message: The user's natural language input
            conversation_history: Previous messages for multi-turn context
            user_context: User info (role, id, name, profile_id)

        Returns:
            tuple: (agent_response, updated_history, actions_taken)
        """
        actions_taken = []

        # Step 1: Dynamically discover tools from MCP server via protocol
        # This calls tools/list on the MCP server - tools are NOT hardcoded
        try:
            await self.mcp_client.discover_tools()
            logger.info("Agent dynamically discovered tools from MCP server")
        except Exception as e:
            logger.error(f"Failed to discover tools from MCP server: {e}")
            return (
                "I'm having trouble connecting to the tool server. Please try again.",
                conversation_history,
                actions_taken,
            )

        # Step 2: Build system prompt with user context
        system = SYSTEM_PROMPT.format(
            today=date.today().strftime("%Y-%m-%d (%A)"),
            role=user_context.get("role", "patient"),
            user_id=user_context.get("user_id", 0),
            profile_id=user_context.get("profile_id", 0),
            user_name=user_context.get("name", "User"),
        )

        # Step 3: Add user message to conversation history
        conversation_history.append({"role": "user", "content": user_message})

        # Step 4: Run agent loop with the appropriate LLM provider
        if self.settings.LLM_PROVIDER == "anthropic" and self.settings.ANTHROPIC_API_KEY:
            response_text, actions_taken = await self._call_anthropic(
                system, conversation_history, actions_taken
            )
        else:
            response_text, actions_taken = await self._call_openai(
                system, conversation_history, actions_taken
            )

        # Step 5: Add assistant response to history
        conversation_history.append({"role": "assistant", "content": response_text})

        return response_text, conversation_history, actions_taken

    async def _call_openai(
        self, system: str, history: list[dict], actions: list[str]
    ) -> tuple[str, list[str]]:
        """
        Execute the agent loop using OpenAI's function calling.

        Tool definitions come from MCP (dynamically discovered),
        and tool calls are routed through the MCP client.
        """
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
        messages = [{"role": "system", "content": system}] + history

        # Get tool definitions dynamically from MCP (not hardcoded)
        tools = self.mcp_client.get_tools_for_llm(format="openai")

        # Agent loop: LLM decides → call tool via MCP → feed result → repeat
        max_iterations = 10
        for iteration in range(max_iterations):
            logger.info(f"Agent loop iteration {iteration + 1}/{max_iterations}")

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )

            choice = response.choices[0]

            # If no tool calls, the LLM has produced its final answer
            if not choice.message.tool_calls:
                return choice.message.content or "I'm sorry, I couldn't process that.", actions

            # Process tool calls through MCP protocol
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                logger.info(f"Agent routing tool call through MCP: {tool_name}({tool_args})")
                actions.append(f"Called {tool_name}")

                # Route through MCP Client → MCP Server (protocol-driven)
                try:
                    result = await self.mcp_client.call_tool(tool_name, tool_args)
                except Exception as e:
                    logger.error(f"MCP tool call failed: {tool_name}: {e}")
                    result = json.dumps({"error": f"Tool execution failed: {str(e)}"})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        return "I've completed processing your request.", actions

    async def _call_anthropic(
        self, system: str, history: list[dict], actions: list[str]
    ) -> tuple[str, list[str]]:
        """
        Execute the agent loop using Anthropic's tool use.

        Tool definitions come from MCP (dynamically discovered),
        and tool calls are routed through the MCP client.
        """
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.settings.ANTHROPIC_API_KEY)

        # Get tool definitions dynamically from MCP (not hardcoded)
        tools = self.mcp_client.get_tools_for_llm(format="anthropic")

        messages = history.copy()

        # Agent loop: LLM decides → call tool via MCP → feed result → repeat
        max_iterations = 10
        for iteration in range(max_iterations):
            logger.info(f"Agent loop iteration {iteration + 1}/{max_iterations}")

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
                # Extract text response - LLM has produced its final answer
                text_blocks = [b.text for b in response.content if b.type == "text"]
                return "\n".join(text_blocks) or "Done.", actions

            # Process tool calls through MCP protocol
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in tool_use_blocks:
                tool_name = block.name
                tool_args = block.input

                logger.info(f"Agent routing tool call through MCP: {tool_name}({tool_args})")
                actions.append(f"Called {tool_name}")

                # Route through MCP Client → MCP Server (protocol-driven)
                try:
                    result = await self.mcp_client.call_tool(tool_name, tool_args)
                except Exception as e:
                    logger.error(f"MCP tool call failed: {tool_name}: {e}")
                    result = json.dumps({"error": f"Tool execution failed: {str(e)}"})

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

        return "I've completed processing your request.", actions
