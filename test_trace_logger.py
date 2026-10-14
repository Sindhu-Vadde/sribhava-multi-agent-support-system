import sqlite3
from types import SimpleNamespace

from trace_logger import create_ticket, log_trace, get_usage
from langgraph_pipeline import route_after_classify


def test_create_ticket_starts_open(temp_db):
    ticket_id = create_ticket("hello")
    conn = sqlite3.connect("tickets.db")
    row = conn.execute(
        "SELECT message, status FROM tickets WHERE id = ?", (ticket_id,)
    ).fetchone()
    conn.close()
    assert row == ("hello", "open")


def test_log_trace_saves_timing_and_tokens(temp_db):
    ticket_id = create_ticket("hello")
    log_trace(ticket_id, "Classifier", "REFUND", "because",
              latency_ms=1200, input_tokens=300, output_tokens=50)
    conn = sqlite3.connect("tickets.db")
    row = conn.execute(
        "SELECT agent_name, decision, latency_ms, input_tokens, output_tokens "
        "FROM traces WHERE ticket_id = ?", (ticket_id,)
    ).fetchone()
    conn.close()
    assert row == ("Classifier", "REFUND", 1200, 300, 50)


def test_get_usage_reads_token_counts():
    usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=4)
    response = SimpleNamespace(usage_metadata=usage)
    assert get_usage(response) == (10, 4)


def test_unclassifiable_goes_straight_to_a_human():
    state = {"classification": {"category": "UNCLASSIFIABLE"}}
    assert route_after_classify(state) == "escalate_unclassified"


def test_unclassifiable_is_caught_in_any_letter_case():
    state = {"classification": {"category": "unclassifiable"}}
    assert route_after_classify(state) == "escalate_unclassified"


def test_a_normal_category_continues_to_the_policy_agent():
    state = {"classification": {"category": "REFUND"}}
    assert route_after_classify(state) == "policy"