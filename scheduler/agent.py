from typing import List, Dict

from scheduler.modules.gcal import GCal
from scheduler.modules.extractor import Extractor
from scheduler.modules.scheduler import Scheduler
from scheduler.modules.models import Schedule, TimeSlot
from scheduler.modules import db
from scheduler import config


class AutoSchedulerAgent:
    def __init__(self):
        cfg = config.load()
        self.duration_minutes = cfg["default_duration_minutes"]
        db.init()
        self.gcal = GCal()
        self.extractor = Extractor()
        self.scheduler = None
        self._pending: Dict[str, Schedule] = {}  # title -> original extracted schedule

    def run(self, conversation_input: str) -> Dict[str, List[TimeSlot]]:
        """
        Extract schedules from conversation and return suggested slots for conflicting
        or time-uncertain schedules. Clean schedules are uploaded immediately.

        Returns: { schedule title -> suggested TimeSlots }
                 Empty list means the schedule was uploaded without conflict.
        """
        # Step 1: Load and sync schedules to local db
        past_schedules = self.gcal.load_past()
        self.gcal.load_future()

        # Step 2: Detect patterns and predict
        self.scheduler = Scheduler(past_schedules)
        self.scheduler.detect_pattern()
        self.scheduler.predict()

        # Step 3: Extract schedules from conversation
        conversation = self.extractor.load_from_string(conversation_input)
        extracted: List[Schedule] = self.extractor.extract_script(conversation)

        results: Dict[str, List[TimeSlot]] = {}

        for schedule in extracted:
            duration = (
                int((schedule.end - schedule.start).total_seconds() / 60)
                if schedule.start else self.duration_minutes
            )

            needs_slot = schedule.start is None or any(
                s.start < schedule.end and s.end > schedule.start
                for s in db.get_slots(schedule.start, schedule.end)
            ) if schedule.start else True

            if needs_slot:
                self._pending[schedule.title] = schedule
                results[schedule.title] = self.scheduler.find_slots(
                    duration_minutes=duration,
                    category=schedule.category,
                )
            else:
                self.gcal.upload(schedule)
                results[schedule.title] = []

        return results

    def confirm(self, title: str, slot: TimeSlot):
        """
        Upload a schedule at the user-selected time slot.
        Call this after the user picks a slot from run() results.
        """
        schedule = self._pending.get(title)
        if not schedule:
            raise ValueError(f"No pending schedule found for '{title}'")

        schedule.start = slot.start
        schedule.end = slot.end
        self.gcal.upload(schedule)
        db.upsert_schedule(schedule)
        del self._pending[title]
