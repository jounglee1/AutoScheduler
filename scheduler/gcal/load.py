from typing import List

from scheduler.models import Schedule


class GCalLoad:
    def __init__(self, service):
        """
        :param service: Authenticated Google Calendar API service (from auth.authenticate()).
        """
        self.service = service

    def load(self, calendar_id: str = "primary", days_ahead: int = 30) -> List[Schedule]:
        """
        Load upcoming schedules from Google Calendar.
        :param calendar_id: Google Calendar ID (default: "primary").
        :param days_ahead: How many days ahead to fetch events.
        :return: List of Schedule objects.
        """
        # TODO: call self.service.events().list(), parse results into Schedule objects
        raise NotImplementedError
