"""
Local SQLite cache for schedules and occupied time slots.
Acts as the single source of truth for conflict checking and prediction state.

Tables:
  schedules  — raw event records (from GCal, extractor, or predictor)
  slots      — occupied time blocks used for conflict checking
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional

from scheduler.modules.models import Schedule, TimeSlot
from scheduler import config


def _db_path() -> str:
    return config.load().get("db", {}).get("path", "local.db")


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
    """Create tables if they don't exist."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS schedules (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                start       TEXT    NOT NULL,
                end         TEXT    NOT NULL,
                description TEXT,
                location    TEXT,
                source      TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'confirmed',
                synced_at   TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS slots (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                start     TEXT NOT NULL,
                end       TEXT NOT NULL,
                title     TEXT,
                source    TEXT NOT NULL,
                status    TEXT NOT NULL DEFAULT 'confirmed'
            );

            CREATE INDEX IF NOT EXISTS idx_slots_start ON slots(start);
        """)


def upsert_schedule(s: Schedule):
    """Insert a schedule if it doesn't already exist (matched by title + start)."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        exists = con.execute(
            "SELECT id FROM schedules WHERE title=? AND start=?",
            (s.title, s.start.isoformat())
        ).fetchone()
        if not exists:
            con.execute(
                "INSERT INTO schedules (title, start, end, description, location, source, status, synced_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (s.title, s.start.isoformat(), s.end.isoformat(),
                 s.description, s.location, s.source, s.status, now)
            )
            _insert_slot(con, s)


def _insert_slot(con: sqlite3.Connection, s: Schedule):
    exists = con.execute(
        "SELECT id FROM slots WHERE title=? AND start=?",
        (s.title, s.start.isoformat())
    ).fetchone()
    if not exists:
        con.execute(
            "INSERT INTO slots (start, end, title, source, status) VALUES (?, ?, ?, ?, ?)",
            (s.start.isoformat(), s.end.isoformat(), s.title, s.source, s.status)
        )


def get_slots(start: datetime, end: datetime) -> List[Schedule]:
    """Return all occupied slots within a time range."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM slots WHERE start < ? AND end > ?",
            (end.isoformat(), start.isoformat())
        ).fetchall()
    return [
        Schedule(
            title=r["title"] or "",
            start=datetime.fromisoformat(r["start"]),
            end=datetime.fromisoformat(r["end"]),
            source=r["source"],
            status=r["status"],
        )
        for r in rows
    ]


def has_predicted(title: str) -> bool:
    """Check if a predicted slot for this title already exists — avoid re-predicting."""
    with _conn() as con:
        row = con.execute(
            "SELECT id FROM slots WHERE title=? AND source='predicted' LIMIT 1",
            (title,)
        ).fetchone()
    return row is not None


def clear_predicted():
    """Remove all tentative predicted slots (e.g. before re-running prediction)."""
    with _conn() as con:
        con.execute("DELETE FROM slots WHERE source='predicted'")
