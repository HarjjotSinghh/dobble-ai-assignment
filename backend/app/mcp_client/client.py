"""
MCP Client - Protocol-level client for dynamic tool discovery and invocation.

This module implements the MCP Client layer of the Host--Client--Server
architecture. It connects to the MCP server subprocess via stdio transport,
discovers available tools/resources/prompts dynamically at runtime through
the MCP protocol (JSON-RPC 2.0), and routes tool calls from the LLM agent.

Architecture:
  ┌─────────────────────────────────────────────────────────────────┐
  │  HOST (FastAPI Application)                                    │
  │                                                                │
  │  ┌──────────────┐     ┌──────────────────────────────────────┐ │
  │  │  LLM Agent   │────>│  MCP Client (this module)            │ │
  │  │  (agent.py)  │     │  - discover_tools()   [tools/list]   │ │
  │  │              │<────│  - call_tool()         [tools/call]   │ │
  │  │  Decides     │     │  - list_resources()                  │ │
  │  │  which tool  │     │  - list_prompts()                    │ │
  │  │  to call     │     │  - get_tools_for_llm() [schema conv] │ │
  │  └──────────────┘     └──────────────┬───────────────────────┘ │
  └──────────────────────────────────────┼─────────────────────────┘
                                         │ stdio transport
                                         │ (JSON-RPC 2.0)
                          ┌──────────────▼───────────────────────┐
                          │  MCP Server (subprocess)             │
                          │  mcp_server/server.py                │
                          └──────────────────────────────────────┘

Key MCP protocol interactions:
  1. initialize    - Handshake with capability negotiation
  2. tools/list    - Dynamic discovery of available tools
  3. tools/call    - Execute a tool with validated arguments
  4. resources/list - Discover available data resources
  5. prompts/list  - Discover prompt templates
"""

import sys
import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Any, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

# Path to the MCP server script
_SERVER_SCRIPT = str(Path(__file__).resolve().parent.parent / "mcp_server" / "server.py")
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent.parent)


class MCPClient:
    """
    MCP Client that manages the connection to the MCP server and provides
    dynamic tool discovery and invocation through the MCP protocol.

    The client maintains a persistent connection to the MCP server subprocess
    for the lifetime of the FastAPI application. Tool schemas are discovered
    dynamically via the protocol, not hardcoded in the agent.

    Lifecycle:
        1. connect()       - Spawn server subprocess, initialize MCP session
        2. discover_tools() - Query available tools via tools/list
        3. call_tool()     - Execute tools via tools/call
        4. disconnect()    - Clean up subprocess and session
    """

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self._exit_stack = AsyncExitStack()
        self._tools_cache: Optional[list] = None
        self._connected = False
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connected and self.session is not None

    async def connect(self) -> None:
        """
        Connect to the MCP server by spawning it as a subprocess.

        This establishes a stdio transport channel and performs the
        MCP initialization handshake (protocol version negotiation
        and capability exchange).

        MCP Protocol Flow:
          Client -> Server: initialize (protocolVersion, capabilities, clientInfo)
          Server -> Client: initialize response (protocolVersion, capabilities, serverInfo)
          Client -> Server: notifications/initialized
        """
        if self._connected:
            logger.info("MCP Client already connected")
            return

        logger.info(f"Connecting MCP Client to server at {_SERVER_SCRIPT}")

        # Build environment for the subprocess - inherit parent env
        # so the MCP server has access to DATABASE_URL, API keys, etc.
        server_env = {**os.environ, "PYTHONPATH": _BACKEND_DIR}

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[_SERVER_SCRIPT],
            env=server_env,
        )

        # Enter the stdio client context - spawns the subprocess
        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport

        # Create and initialize the MCP session (JSON-RPC handshake)
        self.session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        # Perform initialization handshake
        init_result = await self.session.initialize()
        self._connected = True

        logger.info(
            f"MCP Client connected successfully. "
            f"Server: {init_result.serverInfo.name} v{init_result.serverInfo.version}"
        )

        # Pre-cache available tools on connection
        await self.discover_tools()

    async def disconnect(self) -> None:
        """
        Disconnect from the MCP server and clean up resources.
        Terminates the server subprocess.
        """
        if not self._connected:
            return

        logger.info("Disconnecting MCP Client...")
        try:
            await self._exit_stack.aclose()
        except Exception as e:
            logger.warning(f"Error during MCP Client disconnect: {e}")
        finally:
            self.session = None
            self._tools_cache = None
            self._connected = False
            self._exit_stack = AsyncExitStack()
            logger.info("MCP Client disconnected")

    async def discover_tools(self) -> list[dict]:
        """
        Dynamically discover available tools from the MCP server.

        This calls the MCP protocol's tools/list method, which returns
        all tools registered on the server with their schemas. The agent
        uses these schemas to inform the LLM about available capabilities.

        This is the KEY difference from the previous implementation:
        tools are discovered at runtime via the protocol, not hardcoded.

        Returns:
            List of tool metadata dicts with name, description, and inputSchema.
        """
        if not self.is_connected:
            raise RuntimeError("MCP Client not connected. Call connect() first.")

        async with self._lock:
            result = await self.session.list_tools()

        tools = []
        for tool in result.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            })

        self._tools_cache = tools
        logger.info(f"Discovered {len(tools)} tools from MCP server: {[t['name'] for t in tools]}")
        return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """
        Execute a tool on the MCP server via the tools/call protocol method.

        This sends a JSON-RPC request to the server, which dispatches to
        the appropriate tool handler, executes it, and returns the result.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments as a dictionary

        Returns:
            JSON string with the tool execution result

        MCP Protocol Flow:
          Client -> Server: tools/call (name, arguments)
          Server -> Client: result (content: [TextContent | ImageContent])
        """
        if not self.is_connected:
            raise RuntimeError("MCP Client not connected. Call connect() first.")

        logger.info(f"MCP Client calling tool: {tool_name}({json.dumps(arguments, default=str)})")

        async with self._lock:
            result = await self.session.call_tool(tool_name, arguments)

        # Extract text content from the MCP result
        if result.content:
            text_parts = []
            for content_block in result.content:
                if hasattr(content_block, "text"):
                    text_parts.append(content_block.text)
            response = "\n".join(text_parts)
        else:
            response = json.dumps({"error": "Empty response from MCP server"})

        if result.isError:
            logger.warning(f"MCP tool {tool_name} returned an error: {response}")

        return response

    async def list_resources(self) -> list[dict]:
        """
        Discover available resources from the MCP server.

        Resources are read-only data sources (like doctor directories)
        that the agent can reference.

        Returns:
            List of resource metadata dicts.
        """
        if not self.is_connected:
            raise RuntimeError("MCP Client not connected. Call connect() first.")

        async with self._lock:
            result = await self.session.list_resources()

        resources = []
        for resource in result.resources:
            resources.append({
                "uri": str(resource.uri),
                "name": resource.name,
                "description": resource.description,
                "mime_type": resource.mimeType,
            })

        logger.info(f"Discovered {len(resources)} resources from MCP server")
        return resources

    async def list_prompts(self) -> list[dict]:
        """
        Discover available prompt templates from the MCP server.

        Returns:
            List of prompt metadata dicts.
        """
        if not self.is_connected:
            raise RuntimeError("MCP Client not connected. Call connect() first.")

        async with self._lock:
            result = await self.session.list_prompts()

        prompts = []
        for prompt in result.prompts:
            prompts.append({
                "name": prompt.name,
                "description": prompt.description,
                "arguments": [
                    {"name": a.name, "description": a.description, "required": a.required}
                    for a in (prompt.arguments or [])
                ],
            })

        logger.info(f"Discovered {len(prompts)} prompts from MCP server")
        return prompts

    def get_tools_for_llm(self, format: str = "openai") -> list[dict]:
        """
        Convert dynamically discovered MCP tool schemas to LLM-compatible
        function definitions.

        The MCP protocol returns tool schemas in a standard format
        (name, description, inputSchema). This method converts them to
        the format expected by the LLM provider (OpenAI or Anthropic).

        Args:
            format: Target format - "openai" or "anthropic"

        Returns:
            List of tool definitions in the specified LLM format
        """
        if not self._tools_cache:
            raise RuntimeError("No tools discovered. Call discover_tools() first.")

        if format == "openai":
            return [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    },
                }
                for tool in self._tools_cache
            ]
        elif format == "anthropic":
            return [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["input_schema"],
                }
                for tool in self._tools_cache
            ]
        else:
            raise ValueError(f"Unsupported LLM format: {format}")

    async def get_server_capabilities(self) -> dict:
        """
        Return a summary of the MCP server's capabilities.
        Useful for health checks and debugging.
        """
        tools = self._tools_cache or await self.discover_tools()
        resources = await self.list_resources()
        prompts = await self.list_prompts()

        return {
            "connected": self.is_connected,
            "tools": [t["name"] for t in tools],
            "tool_count": len(tools),
            "resources": [r["uri"] for r in resources],
            "resource_count": len(resources),
            "prompts": [p["name"] for p in prompts],
            "prompt_count": len(prompts),
        }
