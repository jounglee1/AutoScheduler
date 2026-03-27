from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Schedule:
    title: str
    id: str = ""
    status: str = "confirmed"   # "confirmed" | "predicted" | "tentative"
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    description: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None


@dataclass
class TimeSlot:
    start: datetime
    end: datetime
    score: float = 0.0
