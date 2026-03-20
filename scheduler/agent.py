from typing import List

from scheduler.modules.gcal import GCal
from scheduler.modules.extractor import Extractor
from scheduler.modules.predictor import Predictor
from scheduler.modules.models import TimeSlot
from scheduler.modules import db
from scheduler import config


class AutoSchedulerAgent:
    def __init__(self):
        cfg = config.load()
        self.duration_minutes = cfg["default_duration_minutes"]
        db.init()
        self.gcal = GCal()
        self.extractor = Extractor()
        self.predictor = None

    def run(self, conversation_input: str) -> List[TimeSlot]:
        """
        Full pipeline:
        1. Load schedules from Google Calendar → synced to local db.
        2. Detect patterns and predict future recurring schedules → stored as tentative slots.
        3. Extract schedules from conversation → upload to GCal + synced to db.
        4. Find candidate time slots by querying local db directly.
        """
        # Step 1: Load and sync schedules to local db
        past_schedules = self.gcal.load_past()
        self.gcal.load_future()

        # Step 2: Detect patterns and predict (skips if already cached in db)
        self.predictor = Predictor(past_schedules)
        self.predictor.detect_pattern()
        self.predictor.predict()

        # Step 3: Extract schedules from conversation and upload
        conversation = self.extractor.load_from_string(conversation_input)
        extracted = self.extractor.extract_script(conversation)
        for schedule in extracted:
            self.gcal.upload(schedule)

        # Step 4: Find slots from local db
        return self.predictor.find_slots(duration_minutes=self.duration_minutes)
