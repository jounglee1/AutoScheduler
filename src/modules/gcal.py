from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List
from uuid import uuid4
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from src.modules.models import Schedule
from src.modules import db
from src import config

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = Path(__file__).parent.parent.parent / "data" / "token.json"


def make_id() -> str:
    """Generate a GCal-compatible event ID: 26-char base32hex (RFC 4648 §7) from UUID4."""
    alphabet = '0123456789abcdefghijklmnopqrstuv'
    num = uuid4().int
    chars = []
    for _ in range(26):
        chars.append(alphabet[num & 0x1f])
        num >>= 5
    return ''.join(reversed(chars))


def get_credentials() -> Credentials:
    if not TOKEN_PATH.exists():
        raise RuntimeError("Not authenticated")
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.expired:
        if not creds.refresh_token:
            TOKEN_PATH.unlink(missing_ok=True)
            raise RuntimeError("No refresh token — please log in again")
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def is_authenticated() -> bool:
    try:
        creds = get_credentials()
        return creds.valid
    except Exception:
        return False


class GCal:
    def __init__(self):
        cfg = config.load()
        self.calendar_id = cfg["gcal"]["calendar_id"]
        self.days_past = cfg["days_past"]
        self.days_ahead = cfg["days_ahead"]

    def _service(self):
        return build("calendar", "v3", credentials=get_credentials())

    def _default_tz(self) -> ZoneInfo:
        """Lazily fetch and cache the calendar's IANA timezone."""
        if not hasattr(self, '_default_tz_cache'):
            result = self._service().calendars().get(calendarId=self.calendar_id).execute()
            self._default_tz_cache = ZoneInfo(result.get("timeZone", "UTC"))
        return self._default_tz_cache

    def _fetch(self, time_min: datetime, time_max: datetime) -> List[Schedule]:
        result = self._service().events().list(
            calendarId=self.calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        schedules = []
        for e in result.get("items", []):
            s = self._parse(e)
            db.upsert_schedule(s)
            schedules.append(s)
        return schedules

    def load_past(self) -> List[Schedule]:
        now = datetime.now(timezone.utc)
        return self._fetch(now - timedelta(days=self.days_past), now)

    def load_future(self) -> List[Schedule]:
        now = datetime.now(timezone.utc)
        return self._fetch(now, now + timedelta(days=self.days_ahead))

    def sync(self):
        """Sync GCal → DB: pull events and remove DB entries deleted from GCal."""
        now = datetime.now(timezone.utc)
        time_min = now - timedelta(days=self.days_past)
        time_max = now + timedelta(days=self.days_ahead)

        result = self._service().events().list(
            calendarId=self.calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        keep_ids = set()
        for e in result.get("items", []):
            if e.get("eventType", "default") != "default":
                continue
            s = self._parse(e)
            keep_ids.add(s.id)
            db.upsert_schedule(s)

        db.delete_stale_gcal(time_min, time_max, keep_ids)

    def upload(self, schedule: Schedule) -> Schedule:
        schedule.id = make_id()
        event = {
            "id": schedule.id,
            "summary": schedule.title,
            "location": schedule.location,
            "description": schedule.description,
            "start": {"dateTime": schedule.start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": schedule.end.isoformat(), "timeZone": "UTC"},
        }
        self._service().events().insert(
            calendarId=self.calendar_id, body=event
        ).execute()
        return schedule

    def delete_event(self, event_id: str):
        self._service().events().delete(
            calendarId=self.calendar_id, eventId=event_id
        ).execute()

    def _parse_dt(self, obj: dict) -> datetime:
        """Parse a GCal start/end object, converted to the calendar's timezone."""
        tz = self._default_tz()
        if "dateTime" in obj:
            return datetime.fromisoformat(obj["dateTime"]).astimezone(tz)
        # All-day event: midnight in the calendar's timezone
        d = datetime.fromisoformat(obj["date"])
        return d.replace(tzinfo=tz)

    def _parse(self, event: dict) -> Schedule:
        return Schedule(
            id=event["id"],
            title=event.get("summary", ""),
            start=self._parse_dt(event["start"]),
            end=self._parse_dt(event["end"]),
            description=event.get("description"),
            location=event.get("location"),
            status="confirmed",
        )
