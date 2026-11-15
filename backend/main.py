from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import sys
import random
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator
from sqlalchemy import ForeignKey, JSON, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from . import auth, private_routes
from .ai import REFERENCES, generate
from .monitor import FIELDS, summarize

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
engine = create_engine(os.getenv("ASTRA_DB_URL", f"sqlite:///{ROOT / 'astra.sqlite3'}"))


class Base(DeclarativeBase):
    pass


class Astronaut(Base):
    __tablename__ = "demo_astronauts"
    id: Mapped[int] = mapped_column(primary_key=True)
    profile: Mapped[dict] = mapped_column(JSON)


class Reading(Base):
    __tablename__ = "demo_readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_id: Mapped[int] = mapped_column(ForeignKey("demo_astronauts.id"), index=True)
    record: Mapped[dict] = mapped_column(JSON)


class Notes(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    symptoms: str = Field(default="", max_length=500)
    wellbeing: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def check_pressure(self):
        if self.systolic is not None and self.diastolic is not None and self.systolic <= self.diastolic:
            raise ValueError("Systolic pressure must exceed diastolic pressure.")
        return self


CheckIn = create_model("CheckIn", __base__=Notes, **{
    key: (Annotated[float, Field(ge=low, le=high)] | None, None)
    for key, (_, _, low, high, _) in FIELDS.items()
})


def now():
    return datetime.now(timezone.utc)


def seed(db):
    if db.scalar(select(Astronaut.id).limit(1)):
        return
    baseline = dict(zip(FIELDS, [62, 116, 74, 36.6, 98, 7.7, 8, 3, 3, 55]))
    rng = random.Random(17)
    today = now()
    for index, (name, role, scenario) in enumerate([
        ("Elena Voss", "Mission Commander", "Stable baseline"),
        ("Amara Chen", "Flight Engineer", "Sleep disruption"),
        ("Mateo Silva", "Mission Specialist", "Rising resting heart rate"),
    ], 1):
        personal = dict(baseline, heart=baseline["heart"] + index - 1, sleep=round(baseline["sleep"] - 0.1 * (index - 1), 1))
        db.add(Astronaut(id=index, profile=dict(name=name, role=role, mission="Asteria I",
               start=(today.date()-timedelta(days=83)).isoformat(), scenario=scenario, baseline=personal)))
        db.flush()
        for day in range(14):
            values = {key: round(value + rng.uniform(-1, 1) * (0.2 if key in ("temperature", "sleep", "oxygen") else 1), 1)
                      for key, value in personal.items()}
            symptoms = ""
            wellbeing = "Routine check-in. Feeling well."
            if index == 2:
                values.update(sleep=round(personal["sleep"] - max(0, day-4)*0.32, 1), fatigue=min(9, 3+max(0, day-4)))
                wellbeing = "Interrupted sleep and feeling tired." if day > 7 else wellbeing
            if index == 3:
                values["heart"] = personal["heart"] + max(0, day-3)*1.6
                symptoms = "Lightheadedness reported during morning routine." if day > 10 else ""
                wellbeing = "Lower energy this morning." if symptoms else wellbeing
            db.add(Reading(astronaut_id=index, record=dict(**values, symptoms=symptoms, wellbeing=wellbeing,
                   timestamp=(today-timedelta(days=13-day, minutes=15)).isoformat())))
    db.commit()


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    auth.Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
    yield


app = FastAPI(title="ASTRA HEALTH", lifespan=lifespan)


def profile(row):
    from datetime import date
    return dict(id=row.id, **row.profile, mission_day=(now().date()-date.fromisoformat(row.profile["start"])).days+1)


def snapshot(db, astronaut_id):
    person = db.get(Astronaut, astronaut_id)
    if not person:
        raise HTTPException(404, "Astronaut not found.")
    history = [row.record for row in db.scalars(select(Reading).where(Reading.astronaut_id == astronaut_id).order_by(Reading.id))]
    history.sort(key=lambda item: item["timestamp"])
    return dict(profile=profile(person), history=history, **summarize(person.profile["baseline"], history))


@app.get("/api/demo/astronauts")
def crew():
    with Session(engine) as db:
        return [profile(row) for row in db.scalars(select(Astronaut).order_by(Astronaut.id))]


@app.get("/api/references")
def references():
    return REFERENCES


@app.get("/api/demo/astronauts/{astronaut_id}")
def dashboard(astronaut_id: int):
    with Session(engine) as db:
        return snapshot(db, astronaut_id)




@app.post("/api/demo/astronauts/{astronaut_id}/ai/{mode}")
def ai(astronaut_id: int, mode: str, body: private_routes.AIRequest):
    if mode not in {"analysis", "chat", "report"}:
        raise HTTPException(404, "Unknown AI mode.")
    if mode == "chat" and not body.question.strip():
        raise HTTPException(422, "Enter a question.")
    with Session(engine) as db:
        data = snapshot(db, astronaut_id)
    return ai_result(mode, body.question, data)


def ai_result(mode, question, data):
    narrative = generate(mode, question, data)
    return dict(narrative=narrative, generated_at=now().isoformat(), profile=data["profile"],
                metrics=data["metrics"], alerts=data["alerts"],
                recorded_at=data["history"][-1]["timestamp"] if data["history"] else None)


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    errors = [dict(loc=item["loc"], msg=item["msg"], type=item["type"]) for item in error.errors()]
    return JSONResponse({"detail": errors}, status_code=422)


@app.middleware("http")
async def protect_api(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        expected = os.getenv("ASTRA_ORIGIN", str(request.base_url).rstrip("/"))
        if request.headers.get("sec-fetch-site") == "cross-site" or (origin and origin != expected):
            return JSONResponse({"detail": "Cross-origin request rejected."}, status_code=403,
                                headers={"Cache-Control": "no-store"})
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(private_routes.routes(sys.modules[__name__]))


if (ROOT / "dist").is_dir():
    app.mount("/", StaticFiles(directory=ROOT / "dist", html=True), name="frontend")

