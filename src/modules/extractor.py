from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from typing_extensions import TypedDict
from zoneinfo import ZoneInfo

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.modules.models import Schedule, TimeSlot
from src.modules import db
from src.prompts import EXTRACT_SCHEDULE_PROMPT
from src import config


class _ProposedSlot(TypedDict):
    start: str   # ISO 8601 with timezone offset
    end: str     # ISO 8601 with timezone offset


class _ExtractedSchedule(TypedDict):
    title: str
    slots: List[_ProposedSlot]
    description: Optional[str]
    location: Optional[str]
    category: str


class _ExtractedScheduleList(TypedDict):
    schedules: List[_ExtractedSchedule]


def _fmt_window(w: list) -> str:
    def _h(h: int) -> str:
        if h == 0:   return "12am"
        if h < 12:   return f"{h}am"
        if h == 12:  return "12pm"
        return f"{h - 12}pm"
    return f"{_h(w[0])}–{_h(w[1])}"


def _build_category_rules(categories: dict) -> str:
    lines = []
    for name, val in categories.items():
        windows = val.get("preferred_time", [])
        if windows:
            times = ", ".join(_fmt_window(w) for w in windows)
            lines.append(f"  - {name}: {times}")
    return "\n".join(lines) if lines else "  - (no category preferences defined)"


class Extractor:
    def __init__(self):
        cfg = config.load()
        model = cfg["extractor"]["model"]
        self.default_duration = timedelta(minutes=cfg.get("default_duration_minutes", 60))
        self.timezone_str = cfg.get("timezone", "UTC")
        self.max_slots = cfg.get("max_slots", 3)
        self.days_ahead = cfg.get("days_ahead", 14)
        categories = cfg.get("categories", {})
        category_names = ", ".join(categories.keys())
        category_rules = _build_category_rules(categories)

        self.llm = ChatOpenAI(model=model).with_structured_output(_ExtractedScheduleList)
        self.prompt = ChatPromptTemplate.from_template(
            EXTRACT_SCHEDULE_PROMPT.format(
                categories=category_names,
                category_rules=category_rules,
                timezone=self.timezone_str,
                max_slots=self.max_slots,
                max_slots_minus_1=max(1, self.max_slots - 1),
                days_ahead=self.days_ahead,
                conversation="{conversation}",
                today="{today}",
            )
        )
        self.chain = self.prompt | self.llm

    def load_from_file(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def load_from_string(self, text: str) -> str:
        return text

    def extract_script(self, conversation: str) -> List[Tuple[Schedule, List[Tuple[datetime, datetime]]]]:
        """Extract schedules and their proposed time slots via LLM."""
        tz = ZoneInfo(self.timezone_str)
        today = datetime.now(tz).strftime("%Y-%m-%d %A")
        result: _ExtractedScheduleList = self.chain.invoke({"conversation": conversation, "today": today})

        def _utc(s: str) -> datetime:
            dt = datetime.fromisoformat(s)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        output = []
        for s in result["schedules"]:
            schedule = Schedule(
                title=s["title"],
                description=s.get("description"),
                location=s.get("location"),
                status="tentative",
                category=s.get("category", "other"),
            )
            proposed: List[Tuple[datetime, datetime]] = []
            for slot in s.get("slots", []):
                try:
                    start = _utc(slot["start"])
                    end = _utc(slot["end"])
                    if end <= start:
                        end = start + self.default_duration
                    proposed.append((start, end))
                except (KeyError, ValueError):
                    continue
            output.append((schedule, proposed))

        return output

    def extract_asr(self, asr_output: str) -> List[Schedule]:
        raise NotImplementedError
