from typing import List

from scheduler.gcal.auth import authenticate
from scheduler.gcal.load import GCalLoad
from scheduler.gcal.upload import GCalUpload
from scheduler.extractor.load_conversation import ConversationLoader
from scheduler.extractor.extract_script import ScheduleExtractor
from scheduler.predictor.predict import SchedulePredictor
from scheduler.predictor.find_slots import SlotFinder
from scheduler.models import Schedule, TimeSlot


class AutoSchedulerAgent:
    def __init__(self, credentials_file: str = "credentials.json"):
        service = authenticate(credentials_file)
        self.gcal_load = GCalLoad(service)
        self.gcal_upload = GCalUpload(service)
        self.conversation_loader = ConversationLoader()
        self.extractor = ScheduleExtractor()
        self.slot_finder = SlotFinder()

    def run(self, conversation_input: str, duration_minutes: int = 60) -> List[TimeSlot]:
        """
        Full pipeline:
        1. Load existing schedules from Google Calendar.
        2. Detect patterns and predict future recurring schedules.
        3. Extract schedules from conversation and upload to Google Calendar.
        4. Find and return candidate time slots avoiding all conflicts.
        """
        # Step 1: Load past schedules
        past_schedules: List[Schedule] = self.gcal_load.load()

        # Step 2: Predict future schedules from patterns
        predictor = SchedulePredictor(past_schedules)
        predicted = predictor.predict()

        # Step 3: Extract schedules from conversation
        conversation = self.conversation_loader.load_from_string(conversation_input)
        extracted = self.extractor.extract(conversation)

        # Step 4: Upload extracted schedules to Google Calendar
        for schedule in extracted:
            self.gcal_upload.upload(schedule)

        # Step 5: Find best available slots
        slots = self.slot_finder.find(
            duration_minutes=duration_minutes,
            existing=past_schedules,
            predicted=predicted,
            extracted=extracted,
        )
        return slots
