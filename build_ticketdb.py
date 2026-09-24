import sqlite3

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

conn.commit()
conn.close()

print("Ticket database created successfully.")