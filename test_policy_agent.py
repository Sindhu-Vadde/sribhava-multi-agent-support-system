import asyncio
import sqlite3
from types import SimpleNamespace

import policy_agent as policy_module
from trace_logger import create_ticket


class FakeSession:
    async def call_tool(self, name, arguments):
        return SimpleNamespace(content=[SimpleNamespace(text="Refunds under $50 may be auto-processed.")])


class FakeModels:
    def generate_content(self, model, contents, config):
        usage = SimpleNamespace(prompt_token_count=11, candidates_token_count=5)
        return SimpleNamespace(text="The refund is small, so no escalation rule applies.", usage_metadata=usage)


def test_policy_agent_returns_the_reasoning_and_logs_a_trace(temp_db, monkeypatch):
    monkeypatch.setattr(policy_module, "gemini_client", SimpleNamespace(models=FakeModels()))
    ticket_id = create_ticket("I want a refund of $20")
    classification = {"category": "REFUND", "intent": "request_refund"}

    result = asyncio.run(policy_module.policy_agent("I want a refund of $20", classification, FakeSession(), ticket_id=ticket_id))

    assert result == "The refund is small, so no escalation rule applies."
    conn = sqlite3.connect("tickets.db")
    row = conn.execute(
        "SELECT agent_name, decision, input_tokens, output_tokens FROM traces WHERE ticket_id = ?", (ticket_id,)
    ).fetchone()
    conn.close()
    assert row == ("Policy", "reasoning_generated", 11, 5)