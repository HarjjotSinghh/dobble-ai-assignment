"""
Chat Router - The main interface for the AI agent.

Handles natural language prompts from users and routes them through
the LLM agent which uses MCP tools (via protocol) to fulfill requests.
Supports multi-turn conversations via structured session management.

MCP Architecture Role:
  This router is part of the HOST layer. It:
  1. Receives user messages via REST API
  2. Manages conversation sessions (multi-turn memory)
  3. Delegates to the agent which uses MCP Client for tool access
  4. Returns structured responses with actions taken

  Flow: Frontend → Chat Router → Agent → MCP Client → MCP Server → Tools
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User, UserRole
from app.schemas.schemas import ChatMessage, ChatResponse
from app.agent.agent import DoctorAppointmentAgent
from app.agent.session import SessionManager

router = APIRouter(prefix="/api/chat", tags=["Chat"])


def _get_mcp_client(request: Request):
    """
    Get the MCP client from application state.

    The MCP client is created once at application startup and stored
    in app.state. It maintains a persistent connection to the MCP
    server subprocess for the lifetime of the application.
    """
    mcp_client = getattr(request.app.state, "mcp_client", None)
    if mcp_client is None or not mcp_client.is_connected:
        raise HTTPException(
            status_code=503,
            detail="MCP server is not available. Please try again later.",
        )
    return mcp_client


@router.post("/", response_model=ChatResponse)
async def chat(
    message: ChatMessage,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a natural language message through the AI agent.

    The agent orchestration flow:
    1. Get/create session for multi-turn conversation continuity
    2. Build user context (role, profile, permissions)
    3. Agent discovers tools dynamically from MCP server [tools/list]
    4. Agent sends prompt + tools to LLM for intent parsing
    5. LLM tool calls are routed via MCP client [tools/call]
    6. Results fed back to LLM for multi-step reasoning
    7. Final response + session saved for next turn

    Multi-turn support: Pass session_id to continue a conversation.
    """
    # Get MCP client from app state (protocol-driven tool access)
    mcp_client = _get_mcp_client(request)

    # Get or create session for conversation continuity
    session_mgr = SessionManager(db)
    session, history = await session_mgr.get_or_create_session(
        user_id=user.id,
        session_id=message.session_id,
    )

    # Build user context for the agent
    user_context = {
        "user_id": user.id,
        "name": user.name,
        "role": user.role.value,
        "profile_id": (
            user.doctor_profile.id if user.role == UserRole.DOCTOR and user.doctor_profile
            else user.patient_profile.id if user.role == UserRole.PATIENT and user.patient_profile
            else 0
        ),
    }

    # Create agent with MCP client (not a DB session - protocol-driven)
    agent = DoctorAppointmentAgent(mcp_client)
    try:
        response_text, updated_history, actions = await agent.process_message(
            user_message=message.message,
            conversation_history=history,
            user_context=user_context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # Save session with structured context (actions, entities, turn count)
    await session_mgr.save_session(
        session,
        updated_history,
        actions_taken=actions,
    )

    return ChatResponse(
        reply=response_text,
        session_id=session.id,
        actions_taken=actions,
    )


@router.get("/sessions")
async def get_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chat session history with structured context (for prompt history tracking)."""
    session_mgr = SessionManager(db)
    return await session_mgr.get_session_history(user.id)
