from typing import List

from scheduler.models import Schedule, TimeSlot


class SlotFinder:
    def find(
        self,
        duration_minutes: int,
        existing: List[Schedule],
        predicted: List[Schedule],
        extracted: List[Schedule],
        search_days: int = 7,
    ) -> List[TimeSlot]:
        """
        Find candidate time slots for a new schedule.
        Avoids conflicts with existing, predicted, and extracted schedules.

        :param duration_minutes: Required duration of the new schedule.
        :param existing: Schedules loaded from Google Calendar.
        :param predicted: Future schedules predicted from patterns.
        :param extracted: Schedules extracted from conversation.
        :param search_days: How many days ahead to search.
        :return: Ranked list of TimeSlot candidates (highest score = best fit).
        """
        # TODO: merge all blocked times, scan candidate windows,
        #       score by preference (e.g. working hours), return ranked slots
        raise NotImplementedError
