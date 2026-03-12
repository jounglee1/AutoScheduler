import json
import subprocess
from datetime import datetime, timedelta, timezone
from typing import List

from scheduler.modules.models import Schedule
from scheduler import config


class GCal:
    def __init__(self):
        cfg = config.load()["gcal"]
        self.calendar_id = cfg["calendar_id"]
        self.days_ahead = cfg["days_ahead"]

    def authenticate(self):
        """
        Authenticate with Google Workspace CLI (gws).
        Runs 'gws auth login' to open a browser-based OAuth flow.
        """
        subprocess.run(["gws", "auth", "login"], check=True)

    def load(self) -> List[Schedule]:
        """Load upcoming schedules from Google Calendar via gws CLI."""
        now = datetime.now(timezone.utc)
        time_max = now + timedelta(days=self.days_ahead)

        params = {
            "calendarId": self.calendar_id,
            "timeMin": now.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": True,
            "orderBy": "startTime",
        }

        result = subprocess.run(
            ["gws", "calendar", "events", "list", "--page-all",
             "--params", json.dumps(params)],
            capture_output=True, text=True, check=True,
        )

        events = json.loads(result.stdout).get("items", [])
        return [self._parse(event) for event in events]

    def upload(self, schedule: Schedule) -> str:
        """Upload a schedule to Google Calendar via gws CLI. Returns created event ID."""
        event = {
            "summary": schedule.title,
            "location": schedule.location,
            "description": schedule.description,
            "start": {"dateTime": schedule.start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": schedule.end.isoformat(), "timeZone": "UTC"},
        }

        result = subprocess.run(
            ["gws", "calendar", "events", "create",
             "--params", json.dumps({"calendarId": self.calendar_id}),
             "--json", json.dumps(event)],
            capture_output=True, text=True, check=True,
        )

        return json.loads(result.stdout).get("id", "")

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
