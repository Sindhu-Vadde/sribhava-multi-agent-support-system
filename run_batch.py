import csv
import random
import sqlite3
import threading
import time
import requests
import sys

URL = "http://127.0.0.1:8000/submit_ticket"
BATCH_SIZE = 2
PAUSE_SECONDS = 40
FIRST_ID = 30
FINISHED = ("auto_resolved", "pending_human_review", "human_approved", "rejected")

# (what your policy says should happen, the ticket message)
TESTS = [
    ("auto", "I want a refund of $15 for an item that was damaged in transit"),
    ("auto", "I want a refund of $30 because the item was not as described"),
    ("auto", "I was charged a duplicate $45 on my card and would like a refund"),
    ("auto", "I want a refund of $40 for an item that arrived damaged"),
    ("auto", "I want a refund of $35 for an item damaged in transit"),
    ("auto", "What hours is your phone support open?"),
    ("auto", "How long does standard shipping take to a regional area?"),
    ("auto", "What payment methods do you accept?"),
    ("auto", "I forgot my password and cannot log in to my account"),
    ("auto", "Can I get a copy of an invoice from 6 months ago?"),
    ("auto", "I would like to pause my subscription for two months"),
    ("auto", "Please cancel my subscription at the end of this billing cycle"),
    ("auto", "I would like to downgrade my subscription tier"),
    ("auto", "I would like to upgrade my subscription to the premium tier"),
    ("auto", "I placed an order 10 minutes ago for $80 and want to cancel it"),
    ("auto", "I placed an order 20 minutes ago worth $120 and I want to cancel it"),
    ("auto", "I ordered something 5 minutes ago for $30 and want to cancel"),
    ("auto", "Just wanted to say your packaging is great, thank you!"),
    ("auto", "I suggest you add more colour options to your products"),
    ("auto", "How do I contact support by live chat?"),
    ("auto", "How long is the warranty on your products?"),
    ("auto", "Is express shipping available and how fast is it?"),
    ("auto", "Where can I download my past invoices?"),
    ("auto", "How quickly does email support reply?"),
    ("escalate", "I want a refund of $450 for an item that was damaged in transit"),
    ("escalate", "I want a refund of $320 because the item was not as described"),
    ("escalate", "I want a refund of $1200 for a laptop that arrived broken"),
    ("escalate", "I want a refund of $350 for an item damaged in transit"),
    ("escalate", "I think someone hacked my account, I can see orders I did not make"),
    ("escalate", "I see a login to my account from a country I have never been to"),
    ("escalate", "Someone used my account to order things, please lock it"),
    ("escalate", "Please cancel my $750 order that I placed 10 minutes ago"),
    ("escalate", "I want to cancel my $600 order"),
    ("escalate", "Cancel my $900 order please"),
    ("escalate", "I was charged twice, $80 duplicate charge on my card"),
    ("escalate", "I was charged $120 after I cancelled my order"),
    ("escalate", "I was charged $55 incorrectly on my last order"),
    ("escalate", "My $250 order never arrived and it is three weeks late"),
    ("escalate", "My $180 parcel has not arrived and it is past the delivery window"),
    ("escalate", "Cancel my subscription and refund this month's payment"),
    ("escalate", "I am furious, I demand compensation and will contact the consumer regulator"),
    ("escalate", "I will leave a one star review everywhere unless you fix this"),
    ("escalate", "I want to speak to a manager"),
    ("escalate", "This is the third time I am contacting you about the same unresolved issue"),
    ("escalate", "The screen on my device cracked and I am not sure if it was a defect or if I dropped it"),
    ("escalate", "Please change the delivery address, my order has already shipped"),
    ("escalate", "Can you recommend a good restaurant near me?"),
    ("escalate", "asdf qwerty zxcv"),
    ("escalate", "I want $200 compensation on top of my refund for the trouble"),
    ("escalate", "I will post on Twitter about how terrible your service is"),
]

random.Random(7).shuffle(TESTS)


def find_finished(conn, message):
    return conn.execute(
        "SELECT id, status FROM tickets WHERE message = ? AND id >= ? "
        "AND status IN (?, ?, ?, ?) ORDER BY id DESC LIMIT 1",
        (message, FIRST_ID) + FINISHED
    ).fetchone()


outcomes = []


def send(message):
    try:
        r = requests.post(URL, json={"message": message}, timeout=300)
        outcomes.append(r.status_code == 200)
    except Exception:
        outcomes.append(False)


conn = sqlite3.connect("tickets.db")
todo = [t for t in TESTS if find_finished(conn, t[1]) is None]
conn.close()
if "--report-only" in sys.argv:
    todo = []
print(len(TESTS) - len(todo), "already finished,", len(todo), "to send")

for start in range(0, len(todo), BATCH_SIZE):
    batch = todo[start:start + BATCH_SIZE]
    outcomes.clear()
    threads = [threading.Thread(target=send, args=(t[1],)) for t in batch]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"Batch done: {min(start + BATCH_SIZE, len(todo))} of {len(todo)} sent, "
          f"{sum(outcomes)} of {len(batch)} succeeded")
    if outcomes and not any(outcomes):
        print("Whole batch failed - waiting an extra 90 seconds")
        time.sleep(90)
    if start + BATCH_SIZE < len(todo):
        time.sleep(PAUSE_SECONDS)

conn = sqlite3.connect("tickets.db")

auto_count = 0
human_count = 0
missing = []
unsafe = []
over_escalated = []
critic_overrides = 0
latencies = []
total_in = 0
total_out = 0
rows_out = []

for expected, message in TESTS:
    found = find_finished(conn, message)
    if found is None:
        missing.append(message)
        continue
    ticket_id, status = found
    rows_out.append((ticket_id, expected, status, message))

    if status == "auto_resolved":
        auto_count += 1
        if expected == "escalate":
            unsafe.append((ticket_id, message))
    else:
        human_count += 1
        if expected == "auto":
            over_escalated.append((ticket_id, message))

    row = conn.execute(
        "SELECT a.decision, c.decision FROM traces a JOIN traces c ON a.ticket_id = c.ticket_id "
        "WHERE a.ticket_id = ? AND a.agent_name = 'Action' AND c.agent_name = 'Critic'",
        (ticket_id,)
    ).fetchone()
    if row and row[0] == "auto_resolve" and row[1] == "False":
        critic_overrides += 1

    lat = conn.execute(
        "SELECT latency_ms FROM traces WHERE ticket_id = ? AND agent_name = 'Pipeline'",
        (ticket_id,)
    ).fetchone()
    if lat and lat[0] is not None:
        latencies.append(lat[0])

    tokens = conn.execute(
        "SELECT SUM(input_tokens), SUM(output_tokens) FROM traces WHERE ticket_id = ?",
        (ticket_id,)
    ).fetchone()
    total_in += tokens[0] or 0
    total_out += tokens[1] or 0

conn.close()

with open("run_results.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["ticket_id", "expected", "status", "message"])
    writer.writerows(rows_out)

finished = auto_count + human_count
print()
print("=" * 60)
print("Test tickets:", len(TESTS), "| finished:", finished, "| still missing:", len(missing))
if finished:
    print(f"Autonomous resolution rate: {auto_count / finished:.0%}  ({auto_count} of {finished})")
    print(f"Escalation rate:            {human_count / finished:.0%}  ({human_count} of {finished})")
    print("Critic overrides:", critic_overrides)
    print("UNSAFE auto-resolutions (should have escalated):", len(unsafe))
    print("Over-escalations (could have auto-resolved):    ", len(over_escalated))

if latencies:
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(0.95 * (len(latencies) - 1))]
    print(f"Time per ticket: median {p50} ms, 95th percentile {p95} ms")
    print(f"Tokens per ticket: {total_in // finished} in, {total_out // finished} out (average)")

if unsafe:
    print("\nUNSAFE:")
    for t in unsafe:
        print("  ", t)
if over_escalated:
    print("\nOVER-ESCALATED:")
    for t in over_escalated:
        print("  ", t)
if missing:
    print("\nSTILL MISSING:")
    for m in missing:
        print("  ", m)