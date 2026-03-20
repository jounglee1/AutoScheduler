from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Schedule:
    title: str
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    description: Optional[str] = None
    location: Optional[str] = None
    source: str = "google_calendar"   # "google_calendar" | "extracted" | "predicted"
    status: str = "confirmed"          # "confirmed" | "tentative"
    category: Optional[str] = None


@dataclass
class TimeSlot:
    start: datetime
    end: datetime
    score: float = 0.0  # Higher = better fit
    reason: Optional[str] = None
