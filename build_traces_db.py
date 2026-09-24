import sqlite3

conn = sqlite3.connect("tickets.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER,
    agent_name TEXT,
    decision TEXT,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("Traces table created successfully.")