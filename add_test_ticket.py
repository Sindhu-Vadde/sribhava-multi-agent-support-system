import sqlite3

conn = sqlite3.connect("tickets.db")
cursor = conn.cursor()

cursor.execute("""
INSERT INTO tickets (message, category, intent, status)
VALUES (?, ?, ?, ?)
""", ("I want to cancel my order, it hasn't shipped yet", "ORDER", "cancel_order", "open"))

conn.commit()

cursor.execute("SELECT * FROM tickets")
print(cursor.fetchall())

conn.close()