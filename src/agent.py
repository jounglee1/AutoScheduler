from datetime import datetime, timezone
from typing import List, Dict, Tuple

from src.modules.gcal import GCal
from src.modules.extractor import Extractor
from src.modules.scheduler import Scheduler
from src.modules.models import Schedule, TimeSlot
from src.modules import db
from src import config


class AutoSchedulerAgent:
    def __init__(self):
        cfg = config.load()
        self.duration_minutes = cfg["default_duration_minutes"]
        db.init()
        self.gcal = GCal()
        self.extractor = Extractor()
        self.scheduler = Scheduler([])

    def run(self, conversation_input: str) -> Dict[str, Tuple[Schedule, List[TimeSlot]]]:
        """
        Extract schedules from conversation and find available slots for each.
        If the schedule has a specific time with no conflict, it is included as the first slot.
        No uploads happen here — call confirm() after the user selects a slot.

        Returns: { title -> (schedule, suggested TimeSlots) }
        """
        # Step 1: Sync all schedules from GCal to local db
        now = datetime.now(timezone.utc)
        all_schedules = self.gcal.sync()
        self.scheduler.past_schedules = [s for s in all_schedules if s.start and s.start < now]

        # Step 2: Detect patterns and predict
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
                slots = [original] + slots[:-1]

            results[schedule.title] = (schedule, slots)

        return results

    def confirm(self, schedule: Schedule, slot: TimeSlot):
        """Upload a schedule at the user-selected slot."""
        schedule.start = slot.start
        schedule.end = slot.end
        self.gcal.upload(schedule)
        db.upsert_schedule(schedule)
