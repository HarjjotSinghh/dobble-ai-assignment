"""
Session Management for Multi-Turn Conversations with Structured Context.

Maintains conversation state between user prompts so the AI agent
can understand references to previously discussed topics. Implements
structured session handling with:

1. Message History   - Chronological conversation messages (capped at 20)
2. Entity Tracking   - Doctors, dates, times mentioned in conversation
3. Action History    - Tools called and their results (for continuity)
4. User Preferences  - Extracted preferences from conversation context

This is a key component of the MCP architecture - the session provides
the "memory" that enables multi-turn, context-aware agent behavior.
"""

import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ChatSession

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages chat sessions for multi-turn conversation support.

    Each session stores:
    - messages: Raw conversation history (last 20 messages)
    - context: Structured context extracted from the conversation
      - entities: Doctors, patients, dates, times referenced
      - preferences: User preferences (preferred doctor, time of day, etc.)
      - action_history: MCP tools called with results (for agent continuity)
      - conversation_summary: Brief summary of conversation so far
    """

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

        # Create new session with structured context
        session = ChatSession(
            user_id=user_id,
            messages=[],
            context=self._create_empty_context(),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session, []

    async def save_session(
        self,
        session: ChatSession,
        messages: list[dict],
        actions_taken: Optional[list[str]] = None,
        context_updates: Optional[dict] = None,
    ) -> None:
        """
        Save updated conversation history and structured context to the session.

        Args:
            session: The chat session to update
            messages: Full conversation history (will be trimmed to last 20)
            actions_taken: List of MCP tools called in this turn
            context_updates: Additional context to merge (entities, preferences)
        """
        # Keep the last 20 messages to prevent context overflow
        session.messages = messages[-20:]

        # Update structured context
        current_context = session.context or self._create_empty_context()

        # Track action history (MCP tools called)
        if actions_taken:
            action_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "actions": actions_taken,
            }
            action_history = current_context.get("action_history", [])
            action_history.append(action_entry)
            # Keep last 10 action entries
            current_context["action_history"] = action_history[-10:]

        # Extract and track entities from conversation
        self._extract_entities(messages, current_context)

        # Merge any explicit context updates
        if context_updates:
            for key, value in context_updates.items():
                if key in current_context:
                    if isinstance(current_context[key], dict) and isinstance(value, dict):
                        current_context[key].update(value)
                    elif isinstance(current_context[key], list) and isinstance(value, list):
                        current_context[key].extend(value)
                    else:
                        current_context[key] = value
                else:
                    current_context[key] = value

        # Update turn counter
        current_context["turn_count"] = current_context.get("turn_count", 0) + 1
        current_context["last_interaction"] = datetime.utcnow().isoformat()

        session.context = current_context
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
                "turn_count": (s.context or {}).get("turn_count", 0),
                "last_message": (
                    s.messages[-1]["content"][:100]
                    if s.messages and len(s.messages) > 0
                    and isinstance(s.messages[-1].get("content"), str)
                    else ""
                ),
                "entities": (s.context or {}).get("entities", {}),
            }
            for s in sessions
        ]

    async def get_session_context(self, session: ChatSession) -> dict:
        """
        Get the structured context for a session.
        Used by the agent to understand conversation state.
        """
        return session.context or self._create_empty_context()

    def _create_empty_context(self) -> dict:
        """Create an empty structured context template."""
        return {
            "entities": {
                "doctors_mentioned": [],
                "dates_mentioned": [],
                "appointments_referenced": [],
            },
            "preferences": {},
            "action_history": [],
            "turn_count": 0,
            "last_interaction": None,
        }

    def _extract_entities(self, messages: list[dict], context: dict) -> None:
        """
        Extract entity references from recent messages to maintain
        structured awareness of what has been discussed.

        This enables the agent to resolve references like "that doctor"
        or "the same time" across conversation turns.
        """
        entities = context.get("entities", {
            "doctors_mentioned": [],
            "dates_mentioned": [],
            "appointments_referenced": [],
        })

        # Process only recent messages (last 4 = last 2 turns)
        recent_messages = messages[-4:] if len(messages) > 4 else messages

        for msg in recent_messages:
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue

            content_lower = content.lower()

            # Track doctor references
            if "dr." in content_lower or "doctor" in content_lower:
                # Extract doctor names mentioned (simple heuristic)
                for word_idx, word in enumerate(content.split()):
                    if word.lower().startswith("dr.") and word_idx + 1 < len(content.split()):
                        name = f"Dr. {content.split()[word_idx + 1]}"
                        if name not in entities["doctors_mentioned"]:
                            entities["doctors_mentioned"].append(name)

            # Track date references
            import re
            date_patterns = re.findall(r'\d{4}-\d{2}-\d{2}', content)
            for date_str in date_patterns:
                if date_str not in entities["dates_mentioned"]:
                    entities["dates_mentioned"].append(date_str)

            # Track appointment IDs
            appt_patterns = re.findall(r'appointment\s*#?(\d+)', content_lower)
            for appt_id in appt_patterns:
                if appt_id not in entities["appointments_referenced"]:
                    entities["appointments_referenced"].append(appt_id)

        # Keep entity lists bounded
        entities["doctors_mentioned"] = entities["doctors_mentioned"][-5:]
        entities["dates_mentioned"] = entities["dates_mentioned"][-5:]
        entities["appointments_referenced"] = entities["appointments_referenced"][-5:]

        context["entities"] = entities
