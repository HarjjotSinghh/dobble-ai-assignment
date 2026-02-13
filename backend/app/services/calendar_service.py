"""
Google Calendar API Service.

Handles creating, updating, and deleting calendar events for appointments.
Falls back gracefully when credentials are not configured.
"""

import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class CalendarService:
    """Google Calendar integration for appointment scheduling."""

    def __init__(self):
        self.service = None
        self._initialized = False

    def _get_service(self):
        """Lazily initialize the Google Calendar API service."""
        if self._initialized:
            return self.service

        self._initialized = True
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import pickle

            SCOPES = ["https://www.googleapis.com/auth/calendar"]
            creds = None

            # Try to load existing token
            if os.path.exists("token.pickle"):
                with open("token.pickle", "rb") as token:
                    creds = pickle.load(token)

            # Refresh or create new credentials
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif not creds and os.path.exists("credentials.json"):
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
                with open("token.pickle", "wb") as token:
                    pickle.dump(creds, token)

            if creds:
                self.service = build("calendar", "v3", credentials=creds)
                logger.info("Google Calendar API initialized successfully")
            else:
                logger.info("Google Calendar credentials not found - running in demo mode")

        except Exception as e:
            logger.info(f"Google Calendar not configured: {e}. Running in demo mode.")

        return self.service

    async def create_event(
        self,
        summary: str,
        description: str,
        start_datetime: datetime,
        end_datetime: datetime,
        attendees: list[str] = None,
    ) -> Optional[str]:
        """Create a Google Calendar event. Returns event ID or None if not configured."""
        service = self._get_service()
        if not service:
            logger.info(f"[Demo Mode] Would create calendar event: {summary} at {start_datetime}")
            return f"demo_event_{start_datetime.strftime('%Y%m%d%H%M')}"

        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_datetime.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": end_datetime.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60},
                    {"method": "popup", "minutes": 30},
                ],
            },
        }

        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        try:
            from app.config import get_settings
            settings = get_settings()
            created_event = service.events().insert(
                calendarId=settings.GOOGLE_CALENDAR_ID, body=event
            ).execute()
            logger.info(f"Calendar event created: {created_event.get('id')}")
            return created_event.get("id")
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None

    async def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        service = self._get_service()
        if not service or event_id.startswith("demo_"):
            return True

        try:
            from app.config import get_settings
            settings = get_settings()
            service.events().delete(
                calendarId=settings.GOOGLE_CALENDAR_ID, eventId=event_id
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete calendar event: {e}")
            return False
