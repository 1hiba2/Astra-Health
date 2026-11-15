from collections import OrderedDict
from hashlib import sha256
import os
from secrets import token_urlsafe
from threading import Lock
from time import monotonic, time

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, model_validator
from typing import Annotated
from sqlalchemy import JSON, ForeignKey, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

COOKIE = "astra_session"
TTL = 8 * 60 * 60
hasher = PasswordHasher()
dummy_hash = hasher.hash(token_urlsafe())
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    profile: Mapped[dict] = mapped_column(JSON)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    digest: Mapped[str] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    expires: Mapped[int] = mapped_column(index=True)


class PrivateReading(Base):
    __tablename__ = "private_readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    record: Mapped[dict] = mapped_column(JSON)


class PrivateAI(Base):
    __tablename__ = "private_ai"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    mode: Mapped[str]
    question: Mapped[str]
    result: Mapped[dict] = mapped_column(JSON)


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Registration(Credentials):
    name: Name
    password: str = Field(min_length=12, max_length=128)
    confirmation: str = Field(max_length=128)

    @model_validator(mode="after")
    def matching_passwords(self):
        if self.password != self.confirmation:
            raise ValueError("Passwords must match.")
        return self


def digest(token):
    return sha256(token.encode()).hexdigest()


def invalidate(db, request):
    token = request.cookies.get(COOKIE)
    if token:
        db.execute(delete(LoginSession).where(LoginSession.digest == digest(token)))


def secure_cookie(request):
    return request.url.scheme == "https" or os.getenv("ASTRA_SECURE_COOKIES") == "1"


def start_session(db, account, request, response):
    invalidate(db, request)
    db.execute(delete(LoginSession).where(LoginSession.expires <= int(time())))
    token = token_urlsafe(32)
    db.add(LoginSession(digest=digest(token), account_id=account.id, expires=int(time()) + TTL))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=TTL, httponly=True, secure=secure_cookie(request), samesite="strict")


def authenticated(db, request):
    token = request.cookies.get(COOKIE)
    session = db.get(LoginSession, digest(token)) if token else None
    if session and session.expires > int(time()):
        account = db.get(Account, session.account_id)
        if account:
            expected = request.headers.get("x-astra-account")
            if expected is None or expected == str(account.id):
                return account
    raise HTTPException(401, "Sign in to access your account.")


def verify(account, password):
    try:
        return hasher.verify(account.password_hash if account else dummy_hash, password) and account is not None
    except VerifyMismatchError:
        return False


_attempts = OrderedDict()
_lock = Lock()


def limit(request, action, maximum):
    ip = request.client.host if request.client else "unknown"
    key = (action, ip)
    current = monotonic()
    with _lock:
        while _attempts and next(iter(_attempts.values()))[0] <= current:
            _attempts.popitem(last=False)
        expires, count = _attempts.get(key, (current + 300, 0))
        if count >= maximum or (key not in _attempts and len(_attempts) >= 10000):
            raise HTTPException(429, "Too many attempts. Try again in five minutes.", headers={"Retry-After": "300"})
        _attempts[key] = (expires, count + 1)

