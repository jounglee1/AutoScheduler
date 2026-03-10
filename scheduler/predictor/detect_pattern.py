from typing import List

from scheduler.models import Schedule


class PatternDetector:
    def __init__(self, past_schedules: List[Schedule]):
        """
        :param past_schedules: Historical schedules loaded from Google Calendar.
        """
        self.past_schedules = past_schedules

    def detect(self) -> dict:
        """
        Group schedules by title and detect recurrence cycles.
        Returns a pattern map: { title -> detected interval in days }
        """
        # TODO: group by title, compute intervals between occurrences,
        #       identify most common interval as the cycle (daily/weekly/monthly)
        raise NotImplementedError
