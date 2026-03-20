from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median, stdev
from typing import List, Optional

from scheduler.modules.models import Schedule, TimeSlot
from scheduler.modules import db
from scheduler import config


class Scheduler:
    def __init__(self, past_schedules: List[Schedule]):
        cfg = config.load()
        self.past_schedules = past_schedules
        self.patterns: dict = {}
        self.days_past = cfg["days_past"]
        self.days_ahead = cfg["days_ahead"]
        self.valid_hour_start = cfg["valid_hour_start"]
        self.valid_hour_end = cfg["valid_hour_end"]

    def detect_pattern(self):
        """
        Group past schedules by title.
        Only accept a cycle if days_past >= interval * 2 (enough data to confirm recurrence).
        Requires low variance (stdev < 2 days or 30% of interval).
        """
        groups: dict = defaultdict(list)
        for s in self.past_schedules:
            groups[s.title].append(s)

        for title, schedules in groups.items():
            if len(schedules) < 2:
                continue

            schedules.sort(key=lambda s: s.start)
            intervals = [
                (schedules[i + 1].start - schedules[i].start).total_seconds() / 86400
                for i in range(len(schedules) - 1)
            ]

            med = median(intervals)
            spread = stdev(intervals) if len(intervals) > 1 else 0

            # reject if variance is too high
            if spread > max(2.0, med * 0.3):
                continue

            # reject if the observation window is too short to confirm the cycle
            if self.days_past < med * 2:
                continue

            durations = [(s.end - s.start) for s in schedules]
            avg_duration = sum(durations, timedelta()) / len(durations)
            last = schedules[-1]

            self.patterns[title] = {
                "interval_days": med,
                "duration": avg_duration,
                "last_start": last.start,
                "location": last.location,
                "description": last.description,
            }

    def predict(self) -> List[Schedule]:
        """
        Project each detected pattern forward up to self.days_ahead days.
        Skips titles that already have predicted slots in the local db (tentative).
        New predictions are written to the db as tentative slots.
        Returns predicted Schedule objects with source="predicted".
        """
        predicted = []
        now = datetime.now(timezone.utc)
        horizon = now + timedelta(days=self.days_ahead)

        for title, p in self.patterns.items():
            if db.has_predicted(title):
                continue  # already cached — skip re-prediction

            interval = timedelta(days=p["interval_days"])
            next_start = p["last_start"] + interval

            while next_start <= horizon:
                if next_start >= now:
                    s = Schedule(
                        title=title,
                        start=next_start,
                        end=next_start + p["duration"],
                        description=p["description"],
                        location=p["location"],
                        source="predicted",
                        status="tentative",
                    )
                    db.upsert_schedule(s)
                    predicted.append(s)
                next_start += interval

        return predicted

    def find_slots(self, duration_minutes: int, category: Optional[str] = None) -> List[TimeSlot]:
        """
        Scan all hours across self.days_ahead for conflict-free slots.
        Queries the local db for all occupied slots (confirmed + tentative).
        Scores by proximity of start time to the category's preferred_time windows.
        Falls back to general scoring if no category is given.
        """
        cfg = config.load()
        preferred_windows = []
        if category and category in cfg.get("categories", {}):
            preferred_windows = cfg["categories"][category].get("preferred_time", [])

        duration = timedelta(minutes=duration_minutes)
        step = timedelta(minutes=30)
        now = datetime.now(timezone.utc)
        end_search = now + timedelta(days=self.days_ahead)
        blocked = db.get_slots(now, end_search)

        slots = []
        candidate = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        while candidate + duration <= end_search:
            slot_end = candidate + duration
            hour = candidate.hour + candidate.minute / 60.0
            end_hour = slot_end.hour + slot_end.minute / 60.0

            # skip outside valid hours
            valid_end = self.valid_hour_end % 24
            if hour < self.valid_hour_start or (valid_end != 0 and end_hour > self.valid_hour_end):
                candidate += step
                continue

            conflict = any(s.start < slot_end and s.end > candidate for s in blocked)
            if not conflict:
                if preferred_windows:
                    # score by proximity to nearest preferred window start
                    min_dist = min(abs(hour - w_start) for w_start, _ in preferred_windows)
                    in_window = any(w_start <= hour < w_end for w_start, w_end in preferred_windows)
                    if in_window:
                        score = 1.0
                    elif min_dist <= 1:
                        score = 0.7
                    elif min_dist <= 2:
                        score = 0.5
                    else:
                        score = 0.3
                else:
                    # general scoring when no category — 10am to 8pm is best
                    h = candidate.hour
                    if 10 <= h < 20:
                        score = 1.0
                    elif 8 <= h < 10 or 20 <= h < 22:
                        score = 0.6
                    else:
                        score = 0.3
                slots.append(TimeSlot(start=candidate, end=slot_end, score=score))

            candidate += step

        max_slots = config.load().get("agent", {}).get("max_slots", 5)
        slots.sort(key=lambda s: -s.score)
        return slots[:max_slots]
