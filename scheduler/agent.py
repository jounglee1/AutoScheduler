from typing import List, Dict, Tuple

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

    def run(self, conversation_input: str) -> Dict[str, Tuple[Schedule, List[TimeSlot]]]:
        """
        Extract schedules from conversation and find available slots for each.
        If the schedule has a specific time with no conflict, it is included as the first slot.
        No uploads happen here — call confirm() after the user selects a slot.

        Returns: { title -> (schedule, suggested TimeSlots) }
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

        results: Dict[str, Tuple[Schedule, List[TimeSlot]]] = {}

        for schedule in extracted:
            duration = (
                int((schedule.end - schedule.start).total_seconds() / 60)
                if schedule.start else self.duration_minutes
            )

            slots = self.scheduler.find_slots(
                duration_minutes=duration,
                category=schedule.category,
            )

            # If the original time has no conflict, prepend it as the top option
            if schedule.start and not any(
                s.start < schedule.end and s.end > schedule.start
                for s in db.get_slots(schedule.start, schedule.end)
            ):
                original = TimeSlot(start=schedule.start, end=schedule.end, score=1.0)
                slots = [original] + slots

            results[schedule.title] = (schedule, slots)

        return results

    def confirm(self, schedule: Schedule, slot: TimeSlot):
        """Upload a schedule at the user-selected slot."""
        schedule.start = slot.start
        schedule.end = slot.end
        self.gcal.upload(schedule)
        db.upsert_schedule(schedule)
