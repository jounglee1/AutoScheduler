import json
import subprocess
from datetime import datetime, timedelta, timezone
from typing import List

from scheduler.modules.models import Schedule
from scheduler.modules import db
from scheduler import config


class GCal:
    def __init__(self):
        cfg = config.load()
        self.calendar_id = cfg["gcal"]["calendar_id"]
        self.days_past = cfg["days_past"]
        self.days_ahead = cfg["days_ahead"]

    def authenticate(self):
        """Authenticate via gws CLI (opens browser OAuth flow)."""
        subprocess.run(["gws", "auth", "login"], check=True)

    def _fetch(self, time_min: datetime, time_max: datetime) -> List[Schedule]:
        params = {
            "calendarId": self.calendar_id,
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": True,
            "orderBy": "startTime",
        }
        result = subprocess.run(
            ["gws", "calendar", "events", "list", "--page-all",
             "--params", json.dumps(params)],
            capture_output=True, text=True, check=True,
        )
        events = []
        for line in result.stdout.strip().splitlines():
            events.extend(json.loads(line).get("items", []))
        schedules = [self._parse(e) for e in events]
        for s in schedules:
            db.upsert_schedule(s)
        return schedules

    def load_past(self) -> List[Schedule]:
        """Load past schedules for pattern detection and prediction."""
        now = datetime.now(timezone.utc)
        return self._fetch(now - timedelta(days=self.days_past), now)

    def load_future(self) -> List[Schedule]:
        """Load upcoming schedules for conflict avoidance."""
        now = datetime.now(timezone.utc)
        return self._fetch(now, now + timedelta(days=self.days_ahead))

    def upload(self, schedule: Schedule) -> str:
        """Upload a schedule to Google Calendar, sync to local db. Returns created event ID."""
        db.upsert_schedule(schedule)
        event = {
            "summary": schedule.title,
            "location": schedule.location,
            "description": schedule.description,
            "start": {"dateTime": schedule.start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": schedule.end.isoformat(), "timeZone": "UTC"},
        }
        result = subprocess.run(
            ["gws", "calendar", "events", "insert",
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
