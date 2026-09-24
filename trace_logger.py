import sqlite3

def log_trace(ticket_id: int, agent_name: str, decision: str, reasoning: str):
    conn = sqlite3.connect("tickets.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO traces (ticket_id, agent_name, decision, reasoning) VALUES (?, ?, ?, ?)",
        (ticket_id, agent_name, decision, reasoning)
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