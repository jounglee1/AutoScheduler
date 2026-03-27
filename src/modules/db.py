"""
Local SQLite cache — single `schedules` table as the source of truth
for display, conflict checking, and prediction state.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.modules.models import Schedule
from src import config


def _db_path() -> str:
    path = config.load().get("db", {}).get("path", "data/local.db")
    root = Path(__file__).parent.parent.parent
    return str(root / path)


@contextmanager
def _conn():
    con = sqlite3.connect(_db_path())
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS schedules (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                start       TEXT NOT NULL,
                end         TEXT NOT NULL,
                description TEXT,
                location    TEXT,
                status      TEXT NOT NULL DEFAULT 'confirmed'
            );

            CREATE INDEX IF NOT EXISTS idx_schedules_start ON schedules(start);
        """)


def _row_to_schedule(r) -> Schedule:
    return Schedule(
        id=r["id"],
        title=r["title"] or "",
        start=datetime.fromisoformat(r["start"]),
        end=datetime.fromisoformat(r["end"]),
        description=r["description"],
        location=r["location"],
        status=r["status"],
    )


def upsert_schedule(s: Schedule):
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO schedules (id, title, start, end, description, location, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (s.id, s.title, s.start.isoformat(), s.end.isoformat(),
             s.description, s.location, s.status)
        )


def get_by_id(schedule_id: str) -> Optional[Schedule]:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM schedules WHERE id=?", (schedule_id,)
        ).fetchone()
    return _row_to_schedule(row) if row else None


def get_slots(start: datetime, end: datetime) -> List[Schedule]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM schedules WHERE start < ? AND end > ?",
            (end.isoformat(), start.isoformat())
        ).fetchall()
    return [_row_to_schedule(r) for r in rows]


def has_predicted(title: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT id FROM schedules WHERE title=? AND status='predicted' LIMIT 1",
            (title,)
        ).fetchone()
    return row is not None


def clear_predicted():
    with _conn() as con:
        con.execute("DELETE FROM schedules WHERE status='predicted'")


def clear_tentative():
    with _conn() as con:
        con.execute("DELETE FROM schedules WHERE status='tentative'")


def delete_stale_gcal(time_min: datetime, time_max: datetime, keep_ids: set):
    """Remove confirmed entries in range no longer present in GCal."""
    with _conn() as con:
        rows = con.execute(
            "SELECT id FROM schedules WHERE status='confirmed' "
            "AND start < ? AND end > ?",
            (time_max.isoformat(), time_min.isoformat())
        ).fetchall()
        for r in rows:
            if r["id"] not in keep_ids:
                con.execute("DELETE FROM schedules WHERE id=?", (r["id"],))


def save_candidates(schedules: List[Schedule]):
    """Replace all tentative candidate entries."""
    with _conn() as con:
        con.execute("DELETE FROM schedules WHERE status='tentative'")
        for s in schedules:
            con.execute(
                "INSERT INTO schedules (id, title, start, end, description, location, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (s.id, s.title, s.start.isoformat(), s.end.isoformat(),
                 s.description, s.location, "tentative")
            )


def delete_candidates_for_title(title: str):
    with _conn() as con:
        con.execute("DELETE FROM schedules WHERE status='tentative' AND title=?", (title,))


def delete_event(schedule_id: str):
    with _conn() as con:
        con.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))


def clear_all():
    with _conn() as con:
        con.execute("DELETE FROM schedules")
