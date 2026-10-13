import sqlite3


def log_trace(ticket_id: int, agent_name: str, decision: str, reasoning: str,
              latency_ms: int = None, input_tokens: int = None, output_tokens: int = None):
    conn = sqlite3.connect("tickets.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO traces (ticket_id, agent_name, decision, reasoning, latency_ms, input_tokens, output_tokens) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ticket_id, agent_name, decision, reasoning, latency_ms, input_tokens, output_tokens)
    )

    conn.commit()
    conn.close()


def create_ticket(message: str) -> int:
    conn = sqlite3.connect("tickets.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO tickets (message, status) VALUES (?, 'open')", (message,))
    conn.commit()

    new_ticket_id = cursor.lastrowid

    conn.close()
    return new_ticket_id

def get_usage(response):
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return None, None
    return usage.prompt_token_count, usage.candidates_token_count