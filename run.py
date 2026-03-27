from dotenv import load_dotenv
load_dotenv()

import os
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # allow HTTP for localhost

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.agent import AutoSchedulerAgent
from src.modules import db
from src.modules.models import Schedule
from src.modules.gcal import make_id
from src.api import auth, events

app = FastAPI(title="AutoScheduler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def _unhandled(_request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": str(exc)})

app.state.agent = AutoSchedulerAgent()
app.state.last_results = {}

app.include_router(auth.router)
app.include_router(events.router)

db.init()


class RunRequest(BaseModel):
    conversation: str


@app.post("/run")
def run(req: RunRequest, request: Request):
    results = request.app.state.agent.run(conversation_input=req.conversation)
    request.app.state.last_results = results

    output = {}
    candidates = []
    for title, (schedule, slots) in results.items():
        output[title] = {
            "schedule": {
                "title": schedule.title,
                "description": schedule.description,
                "location": schedule.location,
                "category": schedule.category,
                "start": schedule.start.isoformat() if schedule.start else None,
                "end": schedule.end.isoformat() if schedule.end else None,
            },
            "slots": [
                {
                    "start": slot.start.isoformat(),
                    "end": slot.end.isoformat(),
                    "score": round(slot.score, 2),
                }
                for slot in slots
            ],
        }
        for slot in slots:
            candidates.append(Schedule(title=title, id=make_id(), start=slot.start,
                                       end=slot.end, status="tentative"))
    db.save_candidates(candidates)
    return output


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("run:app", host="0.0.0.0", port=8001, reload=True)
