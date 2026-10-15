import asyncio

import pytest
from fastapi.testclient import TestClient

import api

HEADERS = {"X-API-Key": "secret"}


class FakeSupervisor:
    """Stands in for the real tool server watchman. 'checks' is the list of
    answers is_healthy() gives, one per call (the last one repeats)."""

    def __init__(self, checks=(True,), has_session=True):
        self.checks = list(checks)
        self.session = object() if has_session else None
        self.restart_count = 0
        self.restart_requested = False

    async def is_healthy(self):
        if len(self.checks) > 1:
            return self.checks.pop(0)
        return self.checks[0]

    def request_restart(self):
        self.restart_requested = True


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    monkeypatch.setattr(api, "WAIT_FOR_TOOL_SERVER_SECONDS", 0)
    return TestClient(api.app)


def post(client, headers=HEADERS):
    return client.post("/submit_ticket", json={"message": "hi"}, headers=headers)


def raising(exc, ticket_id):
    async def fake(message, session):
        exc.ticket_id = ticket_id
        raise exc
    return fake


# ---- API key ---------------------------------------------------------------

def test_missing_key_is_401(client):
    api.app.state.supervisor = FakeSupervisor()
    assert post(client, headers={}).status_code == 401


def test_wrong_key_is_401(client):
    api.app.state.supervisor = FakeSupervisor()
    assert post(client, headers={"X-API-Key": "nope"}).status_code == 401


def test_no_configured_key_is_503(client, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    api.app.state.supervisor = FakeSupervisor()
    assert post(client).status_code == 503


def test_correct_key_processes_ticket(client, monkeypatch):
    async def fake_run(message, session):
        return 123
    monkeypatch.setattr(api, "run_ticket", fake_run)
    api.app.state.supervisor = FakeSupervisor()
    r = post(client)
    assert r.status_code == 200
    assert r.json() == {"ticket_id": 123, "status": "processed"}


# ---- health ------------------------------------------------------------------

def test_health_ok(client):
    api.app.state.supervisor = FakeSupervisor()
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["mcp"] == "up"


def test_health_down(client):
    api.app.state.supervisor = FakeSupervisor(checks=(False,))
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["mcp"] == "down"


# ---- failures: tickets must never be lost ---------------------------------------

def test_tool_server_down_gives_ticket_to_human(client, monkeypatch):
    calls = []
    monkeypatch.setattr(api, "create_ticket", lambda message: 55)
    monkeypatch.setattr(api, "fail_over_to_human", lambda tid, reason: calls.append((tid, reason)))
    api.app.state.supervisor = FakeSupervisor(checks=(False,), has_session=False)

    r = post(client)
    assert r.status_code == 503
    assert r.json()["status"] == "with_human"
    assert r.json()["ticket_id"] == 55
    assert calls and calls[0][0] == 55
    assert calls[0][1].startswith("System failure")


def test_timeout_returns_with_human(client, monkeypatch):
    monkeypatch.setattr(api, "run_ticket", raising(asyncio.TimeoutError(), 77))
    api.app.state.supervisor = FakeSupervisor()
    r = post(client)
    assert r.status_code == 503
    assert r.json()["status"] == "with_human"
    assert r.json()["ticket_id"] == 77


def test_tool_server_dies_midway_gives_ticket_to_human(client, monkeypatch):
    calls = []
    monkeypatch.setattr(api, "run_ticket", raising(RuntimeError("boom"), 88))
    monkeypatch.setattr(api, "fail_over_to_human", lambda tid, reason: calls.append(tid))
    # healthy before the ticket, unhealthy after it fails
    supervisor = FakeSupervisor(checks=(True, False))
    api.app.state.supervisor = supervisor

    r = post(client)
    assert r.status_code == 503
    assert r.json()["ticket_id"] == 88
    assert calls == [88]
    assert supervisor.restart_requested is True


def test_other_error_with_healthy_tool_server_is_500(client, monkeypatch):
    calls = []
    monkeypatch.setattr(api, "run_ticket", raising(ValueError("bad"), 9))
    monkeypatch.setattr(api, "fail_over_to_human", lambda tid, reason: calls.append(tid))
    api.app.state.supervisor = FakeSupervisor(checks=(True,))

    r = post(client)
    assert r.status_code == 500
    assert r.json()["status"] == "error"
    assert r.json()["ticket_id"] == 9
    assert calls == []