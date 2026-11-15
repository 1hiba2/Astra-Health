from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend import auth, main


@pytest.fixture
def clients(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "engine", create_engine(f"sqlite:///{tmp_path / 'test.sqlite3'}"))
    monkeypatch.setattr(auth, "_attempts", auth.OrderedDict())
    with TestClient(main.app) as first:
        yield first, TestClient(main.app)


def register(client, name):
    return client.post("/api/auth/register", json=dict(name=name, email=f"{name}@example.com",
                       password="unique test password", confirmation="unique test password"))


def test_register_login_logout_and_hash(clients):
    client, other = clients
    response = register(client, "alpha")
    assert response.status_code == 201
    assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=strict" in response.headers["set-cookie"]
    token = client.cookies.get(auth.COOKIE)
    with Session(main.engine) as db:
        assert db.scalar(select(auth.Account.password_hash)).startswith("$argon2id$")
        assert db.scalar(select(auth.LoginSession.digest)) == auth.digest(token)
    assert register(other, "alpha").status_code == 409
    credentials = dict(email="alpha@example.com", password="incorrect")
    assert other.post("/api/auth/login", json=credentials).status_code == 401
    credentials["password"] = "unique test password"
    assert other.post("/api/auth/login", json=credentials).status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.set(auth.COOKIE, token)
    assert client.get("/api/me").status_code == 401
    assert other.get("/api/me").status_code == 200


def test_anonymous_and_demo(clients):
    client, _ = clients
    for path in ["/api/auth/session", "/api/me", "/api/me/ai/history"]:
        assert client.get(path).status_code == 401
    assert client.post("/api/me/ai/report", json={"consent": True}).status_code == 401
    assert client.post("/api/me/check-ins", json={"heart": 68}).status_code == 401
    assert client.get("/api/astronauts").status_code == 404
    assert len(client.get("/api/demo/astronauts").json()) == 3
    assert client.post("/api/demo/astronauts/1/check-ins", json={"heart": 71}).status_code in (404, 405)


def test_account_isolation_and_consent(clients, monkeypatch):
    first, second = clients
    alpha = register(first, "alpha").json()["id"]
    beta = register(second, "beta").json()["id"]
    assert first.patch("/api/me/baseline", json={"heart": 62}).status_code == 200
    assert first.post("/api/me/check-ins", json={"heart": 75, "symptoms": "Alpha only"}).status_code == 201
    assert second.post("/api/me/check-ins", json={"heart": 58}).status_code == 201
    assert second.get("/api/me").json()["metrics"]["heart"]["baseline"] is None
    for method in ["GET", "PATCH", "DELETE"]:
        assert first.request(method, f"/api/me/{beta}/check-ins").status_code in (404, 405)
    assert first.get("/api/me", headers={"X-Astra-Account": str(beta)}).status_code == 401
    assert first.get("/api/me?account_id=" + str(beta)).json()["profile"]["id"] == alpha
    assert first.post("/api/me/check-ins", json={"account_id": beta, "heart": 80}).status_code == 422
    assert first.patch("/api/me/profile", json={"name": "Changed", "mission": "Orbit", "role": "Pilot",
                       "start": "2026-01-01"}).json()["profile"]["name"] == "Changed"
    assert second.get("/api/me").json()["history"][-1]["heart"] == 58
    assert first.get("/api/demo/astronauts/1").json()["profile"]["name"] == "Elena Voss"

    def fake(mode, question, data):
        assert data["profile"]["id"] == alpha
        assert [r["heart"] for r in data["history"]] == [75]
        return {"observations": ["Test"]}

    monkeypatch.setattr(main, "generate", fake)
    assert first.post("/api/me/ai/report", json={}).status_code == 422
    assert first.post("/api/me/ai/report", json={"consent": False}).status_code == 422
    assert first.post("/api/me/ai/report", json={"consent": True}).status_code == 200
    assert first.post("/api/me/ai/chat", json={"consent": True, "question": "How am I?"}).status_code == 200
    assert len(first.get("/api/me/ai/history").json()) == 2
    assert second.get("/api/me/ai/history").json() == []


def test_cross_origin_expiry_and_rate_limit(clients, monkeypatch):
    client, _ = clients
    assert client.post("/api/auth/logout", headers={"Origin": "https://other.example"}).status_code == 403
    assert register(client, "alpha").status_code == 201
    assert client.get("/api/me").headers["cache-control"] == "no-store"
    monkeypatch.setattr(auth, "time", lambda: 2**40)
    assert client.get("/api/me").status_code == 401
    monkeypatch.setattr(auth, "verify", lambda *_: False)
    for _ in range(10):
        assert client.post("/api/auth/login", json={"email": "alpha@example.com", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "alpha@example.com", "password": "wrong"}).status_code == 429



def test_https_cookie_and_password_validation(clients):
    client, _ = clients
    password = "this must never appear in a validation response"
    invalid = client.post("/api/auth/register", json=dict(name="Alpha", email="alpha@example.com",
                          password=password, confirmation="mismatch"))
    assert invalid.status_code == 422
    assert password not in invalid.text
    with TestClient(main.app, base_url="https://astra.example") as secure:
        response = register(secure, "alpha")
        assert response.status_code == 201
        assert "; Secure" in response.headers["set-cookie"]
        assert secure.get("/api/me").status_code == 200


def test_legacy_tables_survive_additive_migration(tmp_path, monkeypatch):
    from sqlalchemy import text

    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.sqlite3'}")
    monkeypatch.setattr(main, "engine", engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE astronauts (id INTEGER PRIMARY KEY, profile JSON)"))
        connection.execute(text("CREATE TABLE readings (id INTEGER PRIMARY KEY, astronaut_id INTEGER, record JSON)"))
        connection.execute(text("INSERT INTO astronauts VALUES (99, '{}')"))
        connection.execute(text("INSERT INTO readings VALUES (1, 99, '{}')"))
    with TestClient(main.app) as client:
        assert client.get("/api/demo/astronauts/99").status_code == 404
    with engine.connect() as connection:
        assert connection.execute(text("SELECT * FROM astronauts")).one() == (99, "{}")
        assert connection.execute(text("SELECT * FROM readings")).one() == (1, 99, "{}")


def test_daily_check_in_field_rules(clients):
    from backend.monitor import FIELDS

    client, _ = clients
    assert register(client, "alpha").status_code == 201
    path = "/api/me/check-ins"
    response = client.post(path, json={"wellbeing": "Feeling good overall", "symptoms": "No symptoms"})
    assert response.status_code == 201
    latest = response.json()["history"][-1]
    assert latest["wellbeing"] == "Feeling good overall"
    assert latest["symptoms"] == "No symptoms"
    for key, (_, _, minimum, maximum, _) in FIELDS.items():
        metric = response.json()["metrics"][key]
        assert (metric["minimum"], metric["maximum"]) == (minimum, maximum)
        assert latest[key] is None
        for value in (minimum, maximum):
            assert client.post(path, json={key: value}).status_code == 201
        for value in (minimum - 1, maximum + 1, "text"):
            rejected = client.post(path, json={key: value})
            assert rejected.status_code == 422
            assert rejected.json()["detail"][0]["loc"] == ["body", key]
    for key in ("wellbeing", "symptoms"):
        assert client.post(path, json={key: "x" * 500}).status_code == 201
        assert client.post(path, json={key: "x" * 501}).status_code == 422
        assert client.post(path, json={key: 50}).status_code == 422
    assert client.post(path, json={"systolic": 90, "diastolic": 90}).status_code == 422
