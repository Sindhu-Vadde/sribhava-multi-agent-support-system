import sqlite3


def init_db():
    """Creates the tickets and traces tables if they do not exist yet.
    Safe to run every time the app starts: it never changes existing data."""
    conn = sqlite3.connect("tickets.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT NOT NULL,
        category TEXT,
        intent TEXT,
        status TEXT DEFAULT 'open',
        agent_reasoning TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS traces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER,
        agent_name TEXT,
        decision TEXT,
        reasoning TEXT,
        latency_ms INTEGER,
        input_tokens INTEGER,
        output_tokens INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


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