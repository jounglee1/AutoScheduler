from typing import List

from scheduler.modules.models import Schedule, TimeSlot
from scheduler import config


class Predictor:
    def __init__(self, past_schedules: List[Schedule]):
        """
        :param past_schedules: Historical schedules loaded from Google Calendar.
        """
        cfg = config.load()["predictor"]
        self.past_schedules = past_schedules
        self.patterns: dict = {}
        self.days_ahead = cfg["days_ahead"]
        self.search_days = cfg["search_days"]

    def detect_pattern(self) -> dict:
        """
        Group schedules by title and detect recurrence cycles.
        Returns a pattern map: { title -> detected interval in days }
        """
        # TODO: group by title, compute intervals between occurrences,
        #       identify most common interval as the cycle (daily/weekly/monthly)
        raise NotImplementedError

    def predict(self) -> List[Schedule]:
        """
        Project detected patterns into the future.
        :param days_ahead: How many days ahead to predict.
        :return: List of predicted Schedule objects (source="predicted").
        """
        # TODO: for each pattern, generate future occurrences within self.days_ahead
        raise NotImplementedError

    def find_slots(
        self,
        duration_minutes: int,
        existing: List[Schedule],
        predicted: List[Schedule],
        extracted: List[Schedule],
    ) -> List[TimeSlot]:
        """
        Find candidate time slots avoiding all conflicts.

        :param duration_minutes: Required duration of the new schedule.
        :param existing: Schedules loaded from Google Calendar.
        :param predicted: Future schedules predicted from patterns.
        :param extracted: Schedules extracted from conversation.
        :return: Ranked list of TimeSlot candidates (highest score = best fit).
        """
        # TODO: merge all blocked times, scan candidate windows,
        #       score by preference (e.g. working hours), return ranked slots
        raise NotImplementedError
