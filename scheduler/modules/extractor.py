from datetime import datetime
from typing import List, Optional
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from scheduler.modules.models import Schedule
from scheduler.prompts import EXTRACT_SCHEDULE_PROMPT
from scheduler import config


class _ExtractedSchedule(TypedDict):
    title: str
    start: str        # ISO 8601: "2024-03-10T14:00:00"
    end: str          # ISO 8601: "2024-03-10T15:00:00"
    description: Optional[str]
    location: Optional[str]


class _ExtractedScheduleList(TypedDict):
    schedules: List[_ExtractedSchedule]


class Extractor:
    def __init__(self):
        cfg = config.load()["extractor"]
        model = cfg["model"]
        self.llm = ChatOpenAI(model=model).with_structured_output(_ExtractedScheduleList)
        self.prompt = ChatPromptTemplate.from_template(EXTRACT_SCHEDULE_PROMPT)
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
        return [
            Schedule(
                title=s["title"],
                start=datetime.fromisoformat(s["start"]),
                end=datetime.fromisoformat(s["end"]),
                description=s.get("description"),
                location=s.get("location"),
                source="extracted",
            )
            for s in result["schedules"]
        ]

    def extract_asr(self, asr_output: str) -> List[Schedule]:
        """
        Extract schedules from ASR (Automatic Speech Recognition) output.
        :param asr_output: Raw transcribed text from a speech recognition system.
        """
        # TODO: implement ASR-specific extraction (handle transcription noise, filler words, etc.)
        raise NotImplementedError
