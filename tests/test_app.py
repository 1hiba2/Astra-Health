from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from backend import main, ai


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "engine", create_engine(f"sqlite:///{tmp_path / 'test.sqlite3'}"))
    with TestClient(main.app) as session:
        yield session


def test_seed_and_alerts(client):
    assert len(client.get("/api/demo/astronauts").json()) == 3
    stable, sleep, heart = [client.get(f"/api/demo/astronauts/{i}").json() for i in range(1, 4)]
    assert stable["alerts"] == []
    assert sleep["alerts"][0]["code"] == "sleep_fatigue"
    assert sleep["metrics"]["sleep"]["trend"] < 0
    assert heart["alerts"][0]["code"] == "heart_symptoms"
    assert heart["metrics"]["heart"]["trend"] > 0


def test_ai_without_key(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert client.post("/api/demo/astronauts/2/ai/analysis", json={"consent": True}).status_code == 503
    assert client.get("/api/demo/astronauts/2").status_code == 200


@pytest.mark.parametrize("mode", ["analysis", "chat", "report"])
def test_structured_ai_modes(client, monkeypatch, mode):
    import json
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def fake_generate(**kwargs):
        payload = json.loads(kwargs["contents"])
        assert payload["mode"] == mode
        context = payload["context"]
        assert context["alerts"][0]["code"] == "sleep_fatigue"
        assert not context["history"][-1]["symptoms"]
        assert "profile" not in context
        assert kwargs["config"].max_output_tokens == 1000
        narrative = dict(observations=["Sleep is below baseline."], changes=[], possible_factors=[],
                         follow_up=[], crew_review=[], source_ids=["sleep", "physiology"])
        return SimpleNamespace(text=json.dumps(narrative))

    sdk = MagicMock()
    sdk.return_value.__enter__.return_value.models.generate_content.side_effect = fake_generate
    monkeypatch.setattr(ai.genai, "Client", sdk)
    result = client.post(f"/api/demo/astronauts/2/ai/{mode}", json={"question": "How has my sleep changed?", "consent": True})
    assert result.status_code == 200
    assert result.json()["profile"]["id"] == 2
    assert [item["id"] for item in result.json()["narrative"]["references"]] == ["sleep"]
    assert result.json()["alerts"][0]["level"] == "Crew review"


@pytest.mark.parametrize("status, expected", [(429, "quota"), (403, "project access"), (404, "model is unavailable")])
def test_gemini_errors_are_sanitized(client, monkeypatch, status, expected):
    from unittest.mock import MagicMock

    monkeypatch.setenv("GEMINI_API_KEY", "secret-test-value")
    sdk = MagicMock()
    generate = sdk.return_value.__enter__.return_value.models.generate_content
    generate.side_effect = ai.errors.APIError(status, {"error": {"message": "secret-test-value"}})
    monkeypatch.setattr(ai.genai, "Client", sdk)
    response = client.post("/api/demo/astronauts/2/ai/analysis", json={"consent": True})
    assert response.status_code == (429 if status == 429 else 503)
    assert expected in response.json()["detail"]
    assert "secret-test-value" not in response.text
    assert generate.call_count == 1
