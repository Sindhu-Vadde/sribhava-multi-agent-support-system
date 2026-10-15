import asyncio
import sqlite3

import pytest

import langgraph_pipeline as lp


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    conn = sqlite3.connect("tickets.db")
    conn.execute(
        "CREATE TABLE tickets (id INTEGER PRIMARY KEY, message TEXT, status TEXT, "
        "category TEXT, intent TEXT, agent_reasoning TEXT)"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(lp, "log_trace", lambda *a, **k: None)

    def fake_create_ticket(message):
        c = sqlite3.connect("tickets.db")
        cur = c.execute("INSERT INTO tickets (message, status) VALUES (?, 'open')", (message,))
        c.commit()
        new_id = cur.lastrowid
        c.close()
        return new_id

    monkeypatch.setattr(lp, "create_ticket", fake_create_ticket)


def read_ticket(ticket_id):
    conn = sqlite3.connect("tickets.db")
    row = conn.execute(
        "SELECT status, agent_reasoning FROM tickets WHERE id = ?", (ticket_id,)
    ).fetchone()
    conn.close()
    return row


def test_failover_moves_open_ticket_to_human(temp_db):
    ticket_id = lp.create_ticket("hello")
    changed = lp.fail_over_to_human(ticket_id, "System failure: test")
    assert changed is True
    status, reasoning = read_ticket(ticket_id)
    assert status == "pending_human_review"
    assert reasoning.startswith("System failure")


def test_failover_does_not_overwrite_finished_ticket(temp_db):
    ticket_id = lp.create_ticket("hello")
    conn = sqlite3.connect("tickets.db")
    conn.execute("UPDATE tickets SET status = 'auto_resolved' WHERE id = ?", (ticket_id,))
    conn.commit()
    conn.close()
    changed = lp.fail_over_to_human(ticket_id, "System failure: test")
    assert changed is False
    assert read_ticket(ticket_id)[0] == "auto_resolved"


def test_slow_ticket_times_out_and_goes_to_human(temp_db, monkeypatch):
    async def very_slow(message, session, ticket_id):
        await asyncio.sleep(5)

    monkeypatch.setattr(lp, "process_ticket", very_slow)
    monkeypatch.setattr(lp, "PIPELINE_TIMEOUT_SECONDS", 0.1)

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(lp.run_ticket("slow ticket", session=None))

    status, reasoning = read_ticket(1)
    assert status == "pending_human_review"
    assert "System failure" in reasoning