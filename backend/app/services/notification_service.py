"""
Notification Service.

Handles multiple notification channels:
- Slack: Via webhook for doctor summary reports
- In-app: Real-time notifications via WebSocket
- Can be extended to support WhatsApp, Firebase, etc.
"""

import json
import logging
from typing import Any
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)

# WebSocket connections registry: user_id -> list[WebSocket]
_ws_connections: dict[int, list[Any]] = {}


class NotificationService:
    """Multi-channel notification service."""

    async def send_slack_message(self, message: str) -> bool:
        """Send a message to Slack via webhook."""
        settings = get_settings()

        if not settings.SLACK_WEBHOOK_URL or settings.SLACK_WEBHOOK_URL.startswith("https://hooks.slack.com/services/YOUR"):
            logger.info(f"[Demo Mode] Slack message: {message[:200]}...")
            return True

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.SLACK_WEBHOOK_URL,
                    json={
                        "text": message,
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": message,
                                },
                            }
                        ],
                    },
                    timeout=10,
                )
                response.raise_for_status()
                logger.info("Slack notification sent successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    async def broadcast_notification(self, user_id: int, notification: dict) -> None:
        """Broadcast a notification to connected WebSocket clients."""
        connections = _ws_connections.get(user_id, [])
        disconnected = []

        for ws in connections:
            try:
                await ws.send_json(notification)
            except Exception:
                disconnected.append(ws)

        # Clean up disconnected sockets
        for ws in disconnected:
            connections.remove(ws)

    @staticmethod
    def register_ws(user_id: int, websocket: Any) -> None:
        """Register a WebSocket connection for a user."""
        if user_id not in _ws_connections:
            _ws_connections[user_id] = []
        _ws_connections[user_id].append(websocket)

    @staticmethod
    def unregister_ws(user_id: int, websocket: Any) -> None:
        """Unregister a WebSocket connection."""
        if user_id in _ws_connections:
            _ws_connections[user_id] = [
                ws for ws in _ws_connections[user_id] if ws != websocket
            ]
