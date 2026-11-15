from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, create_model
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import auth
from .monitor import FIELDS, summarize


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    name: auth.Name
    mission: auth.Name
    role: auth.Name
    start: date


Baseline = create_model("Baseline", __config__=ConfigDict(extra="forbid", allow_inf_nan=False), **{
    key: (Annotated[float, Field(ge=low, le=high)] | None, None)
    for key, (_, _, low, high, _) in FIELDS.items()
})


class AIRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(default="", max_length=1200)
    consent: Literal[True]


def routes(core):
    router = APIRouter(prefix="/api")

    def profile(account):
        return dict(id=account.id, **account.profile,
                    mission_day=max(0, (core.now().date() - date.fromisoformat(account.profile["start"])).days + 1))

    def snapshot(db, account):
        history = [row.record for row in db.scalars(select(auth.PrivateReading)
                   .where(auth.PrivateReading.account_id == account.id).order_by(auth.PrivateReading.id))]
        history.sort(key=lambda record: record["timestamp"])
        return dict(profile=profile(account), history=history, **summarize(account.profile["baseline"], history))

    @router.post("/auth/register", status_code=201)
    def register(body: auth.Registration, request: Request, response: Response):
        auth.limit(request, "register", 10)
        with Session(core.engine) as db:
            account = auth.Account(email=body.email.casefold(), password_hash=auth.hasher.hash(body.password),
                                   profile=dict(name=body.name, mission="Personal mission", role="Astronaut",
                                                start=core.now().date().isoformat(), scenario="Private account",
                                                baseline=dict.fromkeys(FIELDS)))
            db.add(account)
            try:
                db.flush()
                auth.start_session(db, account, request, response)
            except IntegrityError:
                raise HTTPException(409, "An account already exists for this email.")
            return profile(account)

    @router.post("/auth/login")
    def login(body: auth.Credentials, request: Request, response: Response):
        auth.limit(request, "login", 10)
        with Session(core.engine) as db:
            account = db.scalar(select(auth.Account).where(auth.Account.email == body.email.casefold()))
            if not auth.verify(account, body.password):
                raise HTTPException(401, "Email or password is incorrect.")
            auth.start_session(db, account, request, response)
            return profile(account)

    @router.get("/auth/session")
    def session(request: Request):
        with Session(core.engine) as db:
            return profile(auth.authenticated(db, request))

    @router.post("/auth/logout", status_code=204)
    def logout(request: Request, response: Response):
        with Session(core.engine) as db:
            auth.invalidate(db, request)
            db.commit()
        response.delete_cookie(auth.COOKIE, httponly=True, secure=auth.secure_cookie(request), samesite="strict")

    @router.get("/me")
    def dashboard(request: Request):
        with Session(core.engine) as db:
            return snapshot(db, auth.authenticated(db, request))

    @router.patch("/me/profile")
    def update_profile(body: Settings, request: Request):
        with Session(core.engine) as db:
            account = auth.authenticated(db, request)
            account.profile = {**account.profile, **body.model_dump(mode="json")}
            db.commit()
            return snapshot(db, account)

    @router.patch("/me/baseline")
    def update_baseline(body: Baseline, request: Request):
        with Session(core.engine) as db:
            account = auth.authenticated(db, request)
            values = {**account.profile["baseline"], **body.model_dump(exclude_unset=True)}
            if values["systolic"] is not None and values["diastolic"] is not None and values["systolic"] <= values["diastolic"]:
                raise HTTPException(422, "Systolic baseline must exceed diastolic baseline.")
            account.profile = {**account.profile, "baseline": values}
            db.commit()
            return snapshot(db, account)

    @router.post("/me/check-ins", status_code=201)
    def check_in(body: core.CheckIn, request: Request):
        with Session(core.engine) as db:
            account = auth.authenticated(db, request)
            db.add(auth.PrivateReading(account_id=account.id, record=dict(**body.model_dump(), timestamp=core.now().isoformat())))
            db.commit()
            return snapshot(db, account)

    @router.get("/me/ai/history")
    def history(request: Request):
        with Session(core.engine) as db:
            account = auth.authenticated(db, request)
            rows = db.scalars(select(auth.PrivateAI).where(auth.PrivateAI.account_id == account.id)
                              .order_by(auth.PrivateAI.id.desc()).limit(50))
            return list(reversed([dict(mode=row.mode, question=row.question, result=row.result) for row in rows]))

    @router.post("/me/ai/{mode}")
    def ai(mode: Literal["analysis", "chat", "report"], body: AIRequest, request: Request):
        with Session(core.engine) as db:
            account = auth.authenticated(db, request)
            if mode == "chat" and not body.question.strip():
                raise HTTPException(422, "Enter a question.")
            account_id = account.id
            data = snapshot(db, account)
        result = core.ai_result(mode, body.question, data)
        with Session(core.engine) as db:
            if auth.authenticated(db, request).id != account_id:
                raise HTTPException(401, "Session changed.")
            db.add(auth.PrivateAI(account_id=account_id, mode=mode, question=body.question, result=result))
            db.commit()
        return result

    return router

