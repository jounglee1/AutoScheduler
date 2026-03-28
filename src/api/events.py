from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.modules import db
from src.modules.models import Schedule
from src import config
from typing import Any

router = APIRouter()


class RemoveEventRequest(BaseModel):
    id: str


class ConfirmRequest(BaseModel):
    title: str
    slot_index: int


@router.get("/events")
def events(year: int, month: int):
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (month // 12), (month % 12) + 1, 1, tzinfo=timezone.utc)
    return [
        {
            "id": s.id,
            "title": s.title,
            "start": s.start.isoformat(),
            "end": s.end.isoformat(),
            "status": s.status,
        }
        for s in db.get_slots(start, end)
    ]


@router.post("/events/remove")
def events_remove(req: RemoveEventRequest):
    schedule = db.get_by_id(req.id)
    db.delete_event(req.id)
    if schedule and schedule.status == "confirmed":
        from src.modules.gcal import GCal
        GCal().delete_event(req.id)
    return {"ok": True}


@router.get("/config")
def get_config():
    return config.load()


@router.post("/config")
def set_config(body: dict[str, Any]):
    cfg = config.load()
    cfg.update(body)
    config.save(cfg)
    return {"ok": True}


@router.post("/events/confirm-predicted")
def confirm_predicted(req: RemoveEventRequest):
    schedule = db.get_by_id(req.id)
    if not schedule:
        return {"error": "Event not found"}
    db.delete_event(schedule.id)
    schedule.status = "confirmed"
    from src.modules.gcal import GCal
    GCal().upload(schedule)
    db.upsert_schedule(schedule)
    return {"ok": True}


@router.post("/events/clear-tentative")
def clear_tentative():
    db.clear_tentative()
    return {"ok": True}


@router.post("/events/clear-predicted")
def clear_predicted():
    db.clear_predicted()
    return {"ok": True}


@router.post("/db/clear")
def db_clear():
    db.clear_all()
    return {"ok": True}


@router.post("/sync")
def sync():
    from src.modules.gcal import GCal
    GCal().sync()
    return {"ok": True}


@router.post("/predict")
def predict(request: Request):
    now = datetime.now(timezone.utc)
    scheduler = request.app.state.agent.scheduler
    scheduler.past_schedules = [
        s for s in db.get_slots(datetime.min.replace(tzinfo=timezone.utc), now)
        if s.status == "confirmed"
    ]
    db.clear_predicted()
    scheduler.detect_pattern()
    scheduler.predict()
    return {"ok": True}


@router.post("/confirm")
def confirm(req: ConfirmRequest, request: Request):
    last_results = request.app.state.last_results
    if req.title not in last_results:
        return {"error": "Title not found. Run /run first."}
    schedule, slots = last_results[req.title]
    if req.slot_index < 0 or req.slot_index >= len(slots):
        return {"error": "Invalid slot index."}
    request.app.state.agent.confirm(schedule, slots[req.slot_index])
    del last_results[req.title]
    db.delete_candidates_for_title(req.title)
    if not last_results:
        db.clear_tentative()
    return {"ok": True}
