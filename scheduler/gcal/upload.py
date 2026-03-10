from scheduler.models import Schedule


class GCalUpload:
    def __init__(self, service):
        """
        :param service: Authenticated Google Calendar API service (from auth.authenticate()).
        """
        self.service = service

    def upload(self, schedule: Schedule, calendar_id: str = "primary") -> str:
        """
        Upload a schedule to Google Calendar.
        :param schedule: Schedule object to upload.
        :param calendar_id: Target Google Calendar ID (default: "primary").
        :return: Created event ID.
        """
        event = {
            "summary": schedule.title,
            "location": schedule.location,
            "description": schedule.description,
            "start": {"dateTime": schedule.start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": schedule.end.isoformat(), "timeZone": "UTC"},
        }
        # TODO: call self.service.events().insert(calendarId=calendar_id, body=event).execute()
        raise NotImplementedError
