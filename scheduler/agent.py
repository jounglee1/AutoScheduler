from typing import List

from scheduler.modules.gcal import GCal
from scheduler.modules.extractor import Extractor
from scheduler.modules.predictor import Predictor
from scheduler.modules.models import Schedule, TimeSlot


class AutoSchedulerAgent:
    def __init__(self):
        self.gcal = GCal()
        self.gcal.authenticate()
        self.extractor = Extractor()
        self.predictor = None  # initialized after loading past schedules

    def run(self, conversation_input: str, duration_minutes: int = 60) -> List[TimeSlot]:
        """
        Full pipeline:
        1. Load existing schedules from Google Calendar.
        2. Detect patterns and predict future recurring schedules.
        3. Extract schedules from conversation and upload to Google Calendar.
        4. Find and return candidate time slots avoiding all conflicts.
        """
        # Step 1: Load past schedules
        past_schedules: List[Schedule] = self.gcal.load()

        # Step 2: Detect patterns and predict future schedules
        self.predictor = Predictor(past_schedules)
        self.predictor.detect_pattern()
        predicted = self.predictor.predict()

        # Step 3: Extract schedules from conversation
        conversation = self.extractor.load_from_string(conversation_input)
        extracted = self.extractor.extract_script(conversation)

        # Step 4: Upload extracted schedules to Google Calendar
        for schedule in extracted:
            self.gcal.upload(schedule)

        # Step 5: Find best available slots
        return self.predictor.find_slots(
            duration_minutes=duration_minutes,
            existing=past_schedules,
            predicted=predicted,
            extracted=extracted,
        )
