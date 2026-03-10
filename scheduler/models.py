from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Schedule:
    title: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    source: str = "google_calendar"  # "google_calendar" | "extracted"


@dataclass
class TimeSlot:
    start: datetime
    end: datetime
    score: float = 0.0  # Higher = better fit
    reason: Optional[str] = None
