import sqlite3

conn = sqlite3.connect("tickets.db")
cursor = conn.cursor()

existing = [row[1] for row in cursor.execute("PRAGMA table_info(traces)")]

for column in ["latency_ms", "input_tokens", "output_tokens"]:
    if column not in existing:
        cursor.execute(f"ALTER TABLE traces ADD COLUMN {column} INTEGER")
        print("Added column:", column)

conn.commit()
conn.close()