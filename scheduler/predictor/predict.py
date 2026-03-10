from typing import List

from scheduler.models import Schedule
from scheduler.predictor.detect_pattern import PatternDetector


class SchedulePredictor:
    def __init__(self, past_schedules: List[Schedule]):
        """
        :param past_schedules: Historical schedules loaded from Google Calendar.
        """
        self.patterns = PatternDetector(past_schedules).detect()

    def predict(self, days_ahead: int = 30) -> List[Schedule]:
        """
        Project detected patterns into the future.
        :param days_ahead: How many days ahead to predict.
        :return: List of predicted Schedule objects (source="predicted").
        """
        # TODO: for each pattern, generate future occurrences within days_ahead
        raise NotImplementedError
