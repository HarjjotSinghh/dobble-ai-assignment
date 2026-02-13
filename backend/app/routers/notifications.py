"""
Notification routes - In-app notifications and WebSocket support.

Provides REST endpoints for notification management and a WebSocket
endpoint for real-time notification delivery.
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.database import get_db, async_session
from app.config import get_settings
from app.routers.auth import get_current_user
from app.models.models import User, Notification
from app.schemas.schemas import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("/", response_model=list[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's notifications."""
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.is_read == False)
    query = query.order_by(Notification.created_at.desc()).limit(50)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return [
        NotificationResponse(
            id=n.id,
            title=n.title,
            message=n.message,
            type=n.type,
            channel=n.channel,
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in notifications
    ]


@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    await db.commit()
    return {"success": True}


@router.put("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read."""
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"success": True}


@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket endpoint for real-time notifications.
    Client connects with JWT token for authentication.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()
    NotificationService.register_ws(user_id, websocket)

    try:
        while True:
            # Keep connection alive, handle pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        NotificationService.unregister_ws(user_id, websocket)
