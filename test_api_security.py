import pytest
from fastapi.testclient import TestClient

import api


class FakeSession:
    async def list_tools(self):
        return []


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-test-key")

    async def fake_run_ticket(message, session):
        return 123

    monkeypatch.setattr(api, "run_ticket", fake_run_ticket)
    api.app.state.session = FakeSession()
    # No "with": the real MCP server is not started in tests.
    yield TestClient(api.app)
    api.app.state.session = None


def test_missing_key_is_rejected(client):
    r = client.post("/submit_ticket", json={"message": "hello"})
    assert r.status_code == 401


def test_wrong_key_is_rejected(client):
    r = client.post("/submit_ticket", json={"message": "hello"},
                    headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_correct_key_is_accepted(client):
    r = client.post("/submit_ticket", json={"message": "hello"},
                    headers={"X-API-Key": "secret-test-key"})
    assert r.status_code == 200
    assert r.json()["ticket_id"] == 123


def test_server_without_a_configured_key_refuses(client, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    r = client.post("/submit_ticket", json={"message": "hello"},
                    headers={"X-API-Key": "anything"})
    assert r.status_code == 503


def test_health_is_public_and_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["mcp"] == "up"


def test_health_reports_down_when_tool_server_missing(client):
    api.app.state.session = None
    r = client.get("/health")
    assert r.status_code == 503