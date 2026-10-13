import sqlite3

conn = sqlite3.connect("tickets.db")
rows = conn.execute(
    "SELECT ticket_id, agent_name, latency_ms FROM traces "
    "WHERE agent_name IN ('MCP startup', 'Pipeline') ORDER BY id"
).fetchall()
for r in rows:
    print(r)
conn.close()