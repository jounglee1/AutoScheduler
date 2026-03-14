import os
from datetime import datetime, timedelta, timezone
from typing import List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from scheduler.modules.models import Schedule
from scheduler import config

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_FILE = "token.json"


class GCal:
    def __init__(self):
        cfg = config.load()["gcal"]
        self.calendar_id = cfg["calendar_id"]
        self.days_past = cfg["days_past"]
        self.days_ahead = cfg["days_ahead"]
        self.client_OAuth_file_path = cfg["client_OAuth_file_path"]
        self.service = None

    def authenticate(self):
        """OAuth2 authentication. Saves token.json after first login."""
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.client_OAuth_file_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        self.service = build("calendar", "v3", credentials=creds)

    def _fetch(self, time_min: datetime, time_max: datetime) -> List[Schedule]:
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        return [self._parse(e) for e in events_result.get("items", [])]

    def load_past(self) -> List[Schedule]:
        """Load past schedules for pattern detection and prediction."""
        now = datetime.now(timezone.utc)
        return self._fetch(now - timedelta(days=self.days_past), now)

    def load_future(self) -> List[Schedule]:
        """Load upcoming schedules for conflict avoidance."""
        now = datetime.now(timezone.utc)
        return self._fetch(now, now + timedelta(days=self.days_ahead))

    def upload(self, schedule: Schedule) -> str:
        """Upload a schedule to Google Calendar. Returns created event ID."""
        event = {
            "summary": schedule.title,
            "location": schedule.location,
            "description": schedule.description,
            "start": {"dateTime": schedule.start.isoformat(), "timeZone": str(schedule.start.tzinfo or "UTC")},
            "end": {"dateTime": schedule.end.isoformat(), "timeZone": str(schedule.end.tzinfo or "UTC")},
        }
        created = self.service.events().insert(
            calendarId=self.calendar_id, body=event
        ).execute()
        return created.get("id", "")

    def _parse(self, event: dict) -> Schedule:
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))
        return Schedule(
            title=event.get("summary", ""),
            start=datetime.fromisoformat(start),
            end=datetime.fromisoformat(end),
            description=event.get("description"),
            location=event.get("location"),
            source="google_calendar",
        )
