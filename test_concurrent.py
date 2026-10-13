import sqlite3
import threading
import requests

URL = "http://127.0.0.1:8000/submit_ticket"

# (what the policy says should happen, the ticket message)
TESTS = [
    ("auto_resolved", "I want a refund of $20 for an item that was damaged in transit"),
    ("escalate", "I want a refund of $400 for an item that was damaged in transit"),
    ("escalate", "I think someone hacked my account, I can see orders I did not make"),
    ("escalate", "I am very unhappy with your service and I will post about it on social media"),
    ("auto_resolved", "What hours is your phone support open?"),
]

results = {}


def send(i, message):
    try:
        r = requests.post(URL, json={"message": message}, timeout=300)
        results[i] = r.json().get("ticket_id") if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception as e:
        results[i] = f"FAILED: {e}"


threads = [threading.Thread(target=send, args=(i, t[1])) for i, t in enumerate(TESTS)]
for t in threads:
    t.start()
for t in threads:
    t.join()

conn = sqlite3.connect("tickets.db")
conn.row_factory = sqlite3.Row

for i, (expected, message) in enumerate(TESTS):
    ticket_id = results[i]
    print("-" * 60)
    print("Message: ", message)
    print("Expected:", expected)
    if isinstance(ticket_id, int):
        row = dict(conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone())
        print("Ticket:  ", ticket_id)
        print("Status:  ", row.get("status"))
        print("Category:", row.get("category"), "/", row.get("intent"))
    else:
        print("Result:  ", ticket_id)

conn.close()