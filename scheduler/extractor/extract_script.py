from datetime import datetime
from typing import List, Optional
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from scheduler.models import Schedule
from scheduler.prompts import EXTRACT_SCHEDULE_PROMPT


class ExtractedSchedule(TypedDict):
    """Structured output schema for a single extracted schedule."""
    title: str
    start: str        # ISO 8601 format: "2024-03-10T14:00:00"
    end: str          # ISO 8601 format: "2024-03-10T15:00:00"
    description: Optional[str]
    location: Optional[str]


class ExtractedScheduleList(TypedDict):
    """Wrapper so LLM returns a list of schedules."""
    schedules: List[ExtractedSchedule]


class ScheduleExtractor:
    def __init__(self, model: str = "gpt-4o"):
        self.llm = ChatOpenAI(model=model).with_structured_output(ExtractedScheduleList)
        self.prompt = ChatPromptTemplate.from_template(EXTRACT_SCHEDULE_PROMPT)
        self.chain = self.prompt | self.llm

    def extract(self, conversation: str) -> List[Schedule]:
        """Extract schedules from a conversation script."""
        result: ExtractedScheduleList = self.chain.invoke({"conversation": conversation})
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
