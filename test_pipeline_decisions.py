import asyncio
import sqlite3
from types import SimpleNamespace

import pytest

import langgraph_pipeline
from action_agent import execute_decision
from langgraph_pipeline import build_graph, run_ticket


class FakeSession:
    """Stands in for the MCP server: it only records which tool was called, and with what."""

    def __init__(self):
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return SimpleNamespace(content=[SimpleNamespace(text=f"fake {name} done")])


def use_fake_agents(monkeypatch, classification=None, action=None, critic=None):
    """Swaps the four Gemini-based agents for fakes that always give fixed answers."""
    classification = classification or {"category": "REFUND", "intent": "request_refund", "reasoning": "fake"}
    action = action or {"decision": "auto_resolve", "reasoning": "fake action reasoning"}
    critic = critic or {"approved": True, "reasoning": "fake critic reasoning"}

    def fake_classify(message, ticket_id=None):
        return classification

    async def fake_policy(message, classification, session, ticket_id=None):
        return "fake policy reasoning"

    def fake_decide(message, classification, reasoning, ticket_id=None):
        return action

    def fake_critic(message, reasoning, proposed, ticket_id=None):
        return critic

    monkeypatch.setattr(langgraph_pipeline, "classify_ticket", fake_classify)
    monkeypatch.setattr(langgraph_pipeline, "policy_agent", fake_policy)
    monkeypatch.setattr(langgraph_pipeline, "decide_action", fake_decide)
    monkeypatch.setattr(langgraph_pipeline, "critic_agent", fake_critic)


def run_graph(session, message="test message"):
    return asyncio.run(build_graph(session).ainvoke({"message": message, "ticket_id": 1}))


def test_escalate_decision_calls_the_escalation_tool():
    session = FakeSession()
    asyncio.run(execute_decision(7, {"decision": "escalate", "reasoning": "needs a human"}, session))
    assert session.calls == [("escalate_to_human", {"ticket_id": 7, "reason": "needs a human"})]


def test_auto_resolve_decision_marks_the_ticket_auto_resolved():
    session = FakeSession()
    asyncio.run(execute_decision(7, {"decision": "auto_resolve", "reasoning": "simple case"}, session))
    assert session.calls == [
        ("update_ticket", {"ticket_id": 7, "status": "auto_resolved", "agent_reasoning": "simple case"})
    ]


def test_critic_veto_turns_an_auto_resolve_into_an_escalation(monkeypatch):
    use_fake_agents(
        monkeypatch,
        action={"decision": "auto_resolve", "reasoning": "looks simple"},
        critic={"approved": False, "reasoning": "the policy needs a human here"},
    )
    session = FakeSession()
    final_state = run_graph(session)

    assert final_state["final_decision"]["decision"] == "escalate"
    assert "Overridden by Critic" in final_state["final_decision"]["reasoning"]
    assert [name for name, _ in session.calls] == ["escalate_to_human"]


def test_approved_auto_resolve_closes_the_ticket(monkeypatch):
    use_fake_agents(
        monkeypatch,
        action={"decision": "auto_resolve", "reasoning": "small refund"},
        critic={"approved": True, "reasoning": "agreed"},
    )
    session = FakeSession()
    run_graph(session)

    assert [name for name, _ in session.calls] == ["update_ticket"]
    assert session.calls[0][1]["status"] == "auto_resolved"


def test_action_escalation_reaches_a_human(monkeypatch):
    use_fake_agents(
        monkeypatch,
        action={"decision": "escalate", "reasoning": "large amount"},
        critic={"approved": True, "reasoning": "agreed"},
    )
    session = FakeSession()
    run_graph(session)

    assert [name for name, _ in session.calls] == ["escalate_to_human"]


def test_unclassifiable_ticket_skips_the_other_agents_and_escalates(temp_db, monkeypatch):
    use_fake_agents(
        monkeypatch,
        classification={"category": "UNCLASSIFIABLE", "intent": "unclassifiable", "reasoning": "nonsense"},
    )

    async def policy_must_not_run(*args, **kwargs):
        raise AssertionError("the Policy agent should have been skipped")

    monkeypatch.setattr(langgraph_pipeline, "policy_agent", policy_must_not_run)

    session = FakeSession()
    final_state = run_graph(session, message="asdf qwerty zxcv")

    assert final_state["final_decision"]["decision"] == "escalate"
    assert [name for name, _ in session.calls] == ["escalate_to_human"]


def test_a_crash_marks_the_ticket_as_error(temp_db, monkeypatch):
    def crashing_classify(message, ticket_id=None):
        raise RuntimeError("Gemini is down")

    monkeypatch.setattr(langgraph_pipeline, "classify_ticket", crashing_classify)

    with pytest.raises(RuntimeError):
        asyncio.run(run_ticket("hello", FakeSession()))

    conn = sqlite3.connect("tickets.db")
    status = conn.execute("SELECT status FROM tickets ORDER BY id DESC LIMIT 1").fetchone()[0]
    conn.close()
    assert status == "error"