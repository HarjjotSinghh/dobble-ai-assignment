"""
Session Management for Multi-Turn Conversations.

Maintains conversation context between user prompts so the AI agent
can understand references to previously discussed topics without
the user needing to restate their entire intent.
"""

import json
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ChatSession

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages chat sessions for multi-turn conversation support."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(
        self, user_id: int, session_id: int | None = None
    ) -> tuple[ChatSession, list[dict]]:
        """
        Get an existing session or create a new one.

        Returns:
            tuple: (session, conversation_history)
        """
        if session_id:
            result = await self.db.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id,
                )
            )
            session = result.scalar_one_or_none()
            if session:
                return session, session.messages or []

        # Create new session
        session = ChatSession(
            user_id=user_id,
            messages=[],
            context={},
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session, []

    async def save_session(
        self,
        session: ChatSession,
        messages: list[dict],
        context: dict | None = None,
    ) -> None:
        """Save updated conversation history and context to the session."""
        # Only keep the last 20 messages to prevent context overflow
        session.messages = messages[-20:]
        if context:
            session.context = context
        session.updated_at = datetime.utcnow()
        await self.db.commit()

    async def get_session_history(self, user_id: int) -> list[dict]:
        """Get all chat sessions for a user (for prompt history tracking)."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(10)
        )
        sessions = result.scalars().all()

        return [
            {
                "id": s.id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "message_count": len(s.messages) if s.messages else 0,
                "last_message": (
                    s.messages[-1]["content"][:100]
                    if s.messages and len(s.messages) > 0
                    else ""
                ),
            }
            for s in sessions
        ]
