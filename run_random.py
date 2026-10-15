"""
run_random.py - measure REAL autonomous / escalation rates on random tickets.

Unlike run_batch.py (a designed test mix), this sends randomly sampled, real
customer messages from the public Bitext dataset, so the rates are not
chosen by us. It also compares the Classifier's category with Bitext's label.

Before running:
  1. Copy tickets.db to tickets_backup.db (this run adds tickets to it).
  2. Start the API in another terminal:  uvicorn api:app
  3. Run:  python run_random.py            (50 tickets)
           python run_random.py 30         (a different number)
           python run_random.py --report-only   (just print the report)

It is safe to stop (Ctrl+C) and run again: finished tickets are skipped.
"""
import csv
import os
import random
import sqlite3
import sys
import threading
import time

import requests
from datasets import load_dataset

from clean_data import clean_and_fill_placeholders

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE = "http://127.0.0.1:8000"
URL = BASE + "/submit_ticket"
HEADERS = {"X-API-Key": os.environ.get("API_KEY", "")}
N = 50
SEED = 2026                 # different from build_eval_set.py (42)
BATCH_SIZE = 2
PAUSE_SECONDS = 40          # same pace as run_batch.py, to respect the quota
MAX_FAILED_BATCHES = 2      # stop (do not burn quota) after this many in a row
START_FILE = "random_run_start.txt"
OUT_FILE = "random_results.csv"
FINISHED = ("auto_resolved", "pending_human_review", "human_approved", "rejected")
PRICE_LOW = (0.15, 1.25)    # $ per 1M tokens (input, output) - verify at ai.google.dev/pricing
PRICE_HIGH = (0.30, 2.50)

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if args:
    N = int(args[0])
REPORT_ONLY = "--report-only" in sys.argv


def build_sample():
    dataset = load_dataset("bitext/Bitext-customer-support-llm-chatbot-training-dataset")
    train = dataset["train"]
    rng = random.Random(SEED)
    picks = rng.sample(range(len(train)), N * 3)
    sample, seen = [], set()
    for i in picks:
        row = train[i]
        message = clean_and_fill_placeholders(row["instruction"])
        if message in seen:
            continue
        seen.add(message)
        sample.append({
            "message": message,
            "true_category": row["category"],
            "true_intent": row["intent"],
        })
        if len(sample) == N:
            break
    return sample


def find_finished(conn, message, start_id):
    return conn.execute(
        "SELECT id, status, category, intent FROM tickets WHERE message = ? AND id > ? "
        "AND status IN (?, ?, ?, ?) ORDER BY id DESC LIMIT 1",
        (message, start_id) + FINISHED,
    ).fetchone()


outcomes = []


def send(message):
    try:
        r = requests.post(URL, json={"message": message}, headers=HEADERS, timeout=300)
        outcomes.append(r.status_code == 200)
    except Exception:
        outcomes.append(False)


# ---- setup ---------------------------------------------------------------
if not os.path.exists("tickets.db"):
    sys.exit("tickets.db not found. Run this from the project folder.")

if not REPORT_ONLY:
    if not HEADERS["X-API-Key"]:
        sys.exit("No API_KEY found. Add API_KEY=... to your .env file.")
    try:
        requests.get(BASE + "/health", timeout=5)
    except Exception:
        sys.exit("Cannot reach the API. Start it first in another terminal: uvicorn api:app")

conn = sqlite3.connect("tickets.db")
if os.path.exists(START_FILE):
    start_id = int(open(START_FILE).read().strip())
elif REPORT_ONLY:
    conn.close()
    sys.exit("No random_run_start.txt yet - run without --report-only first.")
else:
    start_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM tickets").fetchone()[0]
    with open(START_FILE, "w") as f:
        f.write(str(start_id))
print("Only tickets with id >", start_id, "are counted in this run.")

sample = build_sample()
todo = [t for t in sample if find_finished(conn, t["message"], start_id) is None]
conn.close()
if REPORT_ONLY:
    todo = []
print(len(sample) - len(todo), "already finished,", len(todo), "to send")

# ---- send in small batches -------------------------------------------------
failed_in_a_row = 0
for start in range(0, len(todo), BATCH_SIZE):
    batch = todo[start:start + BATCH_SIZE]
    outcomes.clear()
    threads = [threading.Thread(target=send, args=(t["message"],)) for t in batch]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"Batch done: {min(start + BATCH_SIZE, len(todo))} of {len(todo)} sent, "
          f"{sum(outcomes)} of {len(batch)} succeeded")
    if outcomes and not any(outcomes):
        failed_in_a_row += 1
        if failed_in_a_row >= MAX_FAILED_BATCHES:
            print("Stopping: batches keep failing (probably the Gemini quota). "
                  "Wait, then run the same command again - finished tickets are skipped.")
            break
        print("Whole batch failed - waiting an extra 90 seconds")
        time.sleep(90)
    else:
        failed_in_a_row = 0
    if start + BATCH_SIZE < len(todo):
        time.sleep(PAUSE_SECONDS)

# ---- report ------------------------------------------------------------------
conn = sqlite3.connect("tickets.db")
auto_count = human_count = category_right = critic_overrides = 0
latencies, rows_out, missing = [], [], []
total_in = total_out = 0

for t in sample:
    found = find_finished(conn, t["message"], start_id)
    if found is None:
        missing.append(t["message"])
        continue
    ticket_id, status, pred_cat, pred_intent = found
    match = (pred_cat or "").strip().upper() == t["true_category"].strip().upper()
    category_right += match
    rows_out.append((ticket_id, status, t["true_category"], pred_cat, match,
                     t["true_intent"], pred_intent, t["message"]))

    if status == "auto_resolved":
        auto_count += 1
    else:
        human_count += 1

    row = conn.execute(
        "SELECT a.decision, c.decision FROM traces a JOIN traces c ON a.ticket_id = c.ticket_id "
        "WHERE a.ticket_id = ? AND a.agent_name = 'Action' AND c.agent_name = 'Critic'",
        (ticket_id,),
    ).fetchone()
    if row and row[0] == "auto_resolve" and row[1] == "False":
        critic_overrides += 1

    lat = conn.execute(
        "SELECT latency_ms FROM traces WHERE ticket_id = ? AND agent_name = 'Pipeline'",
        (ticket_id,),
    ).fetchone()
    if lat and lat[0] is not None:
        latencies.append(lat[0])

    tokens = conn.execute(
        "SELECT SUM(input_tokens), SUM(output_tokens) FROM traces WHERE ticket_id = ?",
        (ticket_id,),
    ).fetchone()
    total_in += tokens[0] or 0
    total_out += tokens[1] or 0

error_tickets = conn.execute(
    "SELECT COUNT(*) FROM tickets WHERE id > ? AND status = 'error'", (start_id,)
).fetchone()[0]
conn.close()

with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["ticket_id", "status", "true_category", "predicted_category",
                "category_match", "true_intent", "predicted_intent", "message"])
    w.writerows(rows_out)

finished = auto_count + human_count
print()
print("=" * 60)
print("Random tickets:", len(sample), "| finished:", finished, "| still missing:", len(missing))
print("Tickets that ended in an error during this run:", error_tickets)
if finished:
    print(f"Autonomous resolution rate: {auto_count / finished:.0%}  ({auto_count} of {finished})")
    print(f"Escalation rate:            {human_count / finished:.0%}  ({human_count} of {finished})")
    print("Critic overrides:", critic_overrides)
    print(f"Category accuracy vs Bitext labels: {category_right / finished:.0%}  "
          f"({category_right} of {finished})")
    avg_in, avg_out = total_in / finished, total_out / finished
    print(f"Tokens per ticket: {avg_in:.0f} in, {avg_out:.0f} out (average)")
    low = (avg_in * PRICE_LOW[0] + avg_out * PRICE_LOW[1]) / 1_000_000
    high = (avg_in * PRICE_HIGH[0] + avg_out * PRICE_HIGH[1]) / 1_000_000
    print(f"Estimated cost per ticket: ${low:.4f} - ${high:.4f} (paid-tier estimate)")
if latencies:
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(0.95 * (len(latencies) - 1))]
    print(f"Time per ticket: median {p50} ms, 95th percentile {p95} ms")
print("Details saved to", OUT_FILE)
if missing:
    print("\nSTILL MISSING (run the same command again to retry):", len(missing))
print("\nNote: these are real, randomly sampled Bitext messages, so the rates reflect")
print("that dataset's mix of requests, not your company's real traffic.")