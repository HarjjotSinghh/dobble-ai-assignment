"""
Chat routes - The main interface for the AI agent.

Handles natural language prompts from users and routes them through
the LLM agent which uses MCP tools to fulfill requests.
Supports multi-turn conversations via session management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User, UserRole
from app.schemas.schemas import ChatMessage, ChatResponse
from app.agent.agent import DoctorAppointmentAgent
from app.agent.session import SessionManager

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    message: ChatMessage,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a natural language message through the AI agent.

    The agent will:
    1. Parse the user's intent
    2. Select appropriate MCP tools
    3. Execute tool calls (check availability, book, notify, etc.)
    4. Return a human-readable response

    Multi-turn support: Pass session_id to continue a conversation.
    """
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

    # Process through the LLM agent
    agent = DoctorAppointmentAgent(db)
    try:
        response_text, updated_history, actions = await agent.process_message(
            user_message=message.message,
            conversation_history=history,
            user_context=user_context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # Save session for multi-turn continuity
    await session_mgr.save_session(session, updated_history)

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
    """Get chat session history for prompt history tracking (Bonus feature)."""
    session_mgr = SessionManager(db)
    return await session_mgr.get_session_history(user.id)
