from datetime import datetime, timedelta
from typing import List, Optional
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from scheduler.modules.models import Schedule
from scheduler.modules import db
from scheduler.prompts import EXTRACT_SCHEDULE_PROMPT
from scheduler import config


class _ExtractedSchedule(TypedDict):
    title: str
    start: Optional[str]  # ISO 8601 with timezone e.g. "2026-03-10T14:00:00-08:00" — None if time not mentioned
    end: Optional[str]    # ISO 8601 with timezone e.g. "2026-03-10T15:00:00-08:00" — None if time not mentioned
    description: Optional[str]
    location: Optional[str]
    category: str         # one of the categories defined in config.yaml, use "other" if unsure


class _ExtractedScheduleList(TypedDict):
    schedules: List[_ExtractedSchedule]


class Extractor:
    def __init__(self):
        cfg = config.load()
        model = cfg["extractor"]["model"]
        self.default_duration = timedelta(minutes=cfg.get("default_duration_minutes", 300))
        categories = ", ".join(cfg.get("categories", {}).keys())
        self.llm = ChatOpenAI(model=model).with_structured_output(_ExtractedScheduleList)
        self.prompt = ChatPromptTemplate.from_template(
            EXTRACT_SCHEDULE_PROMPT.format(categories=categories, conversation="{conversation}")
        )
        self.chain = self.prompt | self.llm

    def load_from_file(self, file_path: str) -> str:
        """Load a conversation script from a text file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def load_from_string(self, text: str) -> str:
        """Accept a raw conversation string directly."""
        return text

    def extract_script(self, conversation: str) -> List[Schedule]:
        """Extract schedules from a conversation script via LLM."""
        result: _ExtractedScheduleList = self.chain.invoke({"conversation": conversation})
        schedules = []
        for s in result["schedules"]:
            raw_start = s.get("start")
            raw_end = s.get("end")

            if raw_start:
                start = datetime.fromisoformat(raw_start)
                end = datetime.fromisoformat(raw_end) if raw_end else start + self.default_duration
                if end <= start:
                    end = start + self.default_duration
            else:
                start = None  # uncertain time — find_slots will be called in agent
                end = None

            schedules.append(Schedule(
                title=s["title"],
                start=start,
                end=end,
                description=s.get("description"),
                location=s.get("location"),
                source="extracted",
                category=s.get("category", "other"),
            ))
        for s in schedules:
            if s.start:
                db.upsert_schedule(s)
        return schedules

    def extract_asr(self, asr_output: str) -> List[Schedule]:
        """
        Extract schedules from ASR (Automatic Speech Recognition) output.
        :param asr_output: Raw transcribed text from a speech recognition system.
        """
        # TODO: implement ASR-specific extraction (handle transcription noise, filler words, etc.)
        raise NotImplementedError
