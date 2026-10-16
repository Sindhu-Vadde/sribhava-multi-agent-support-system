"""
send_demo.py - send 50 demo support tickets, in a random order, to the cloud server.

Same careful pace as run_random.py so the Gemini free-tier quota is not used up:
  - 2 tickets at a time, then a pause
  - stops (without burning quota) if whole batches keep failing
  - safe to stop (Ctrl+C) and run again: tickets that already worked are skipped
    (they are remembered in demo_progress.json)

Before running, set the server address and password in the same terminal:
  $env:SRIBHAVA_API_URL="http://YOUR-IP:8000"
  $env:API_KEY="your-server-api-password"
Then:  python send_demo.py
To start again from zero, delete demo_progress.json first.
"""
import json
import os
import random
import sys
import threading
import time
from collections import Counter

import requests

BASE = os.environ.get("SRIBHAVA_API_URL", "http://127.0.0.1:8000").rstrip("/")
URL = BASE + "/submit_ticket"
KEY = os.environ.get("API_KEY", "")
HEADERS = {"X-API-Key": KEY}

BATCH_SIZE = 2
PAUSE_SECONDS = int(os.environ.get("DEMO_PAUSE_SECONDS", "40"))   # same pace as run_random.py
MAX_FAILED_BATCHES = 2        # stop after this many fully failed batches in a row
PROGRESS_FILE = "demo_progress.json"

TICKETS = [
    "Hi, I placed order 48213 about 20 minutes ago for 89 dollars and it still shows as Confirmed, not Processing. Please cancel it.",
    "Please cancel order 51877. I ordered it 35 minutes ago, the total was 142 dollars, and the status has not moved past Confirmed.",
    "I ordered a jacket for 64 dollars ten minutes ago, order 50102, by mistake. It is still in Confirmed status. Can you cancel it?",
    "I want to cancel my order.",
    "Please cancel order 47990. I placed it yesterday afternoon and it now shows Processing. The total was 120 dollars.",
    "Please cancel order 52044, total 749 dollars. I placed it 15 minutes ago and it is still Confirmed.",
    "Order 49555 arrived with a cracked screen, and I can send a photo. The item cost 79 dollars. Please refund it to my original card.",
    "My order 50911, a 38 dollar pair of headphones, arrived in the wrong colour. The listing said black but I received white. Please refund me.",
    "I was charged twice for order 48870, 45 dollars each, on the same day. Please refund the duplicate charge.",
    "Order 50610, a 28 dollar phone case, is not as described. The listing said leather but it is clearly plastic. Please refund me.",
    "Order 46201 was delivered 6 days ago. I changed my mind about the 60 dollar desk lamp and it is unused in the box. Can I return it for a refund?",
    "My 450 dollar laptop bag from order 50333 arrived damaged in transit. I would like a refund.",
    "I want a refund.",
    "I want my money back for order 49101 because I found the same item cheaper elsewhere. It cost 120 dollars.",
    "I can't log in to my account. I think I forgot my password. How do I get back in?",
    "My account says too many attempts. I just need to reset my password, where is the link?",
    "I need to change the email on my account because my old email no longer works. My last order was 49200 and my billing address is 12 Wattle Street, Parramatta.",
    "There are three orders on my account that I never made, and I got a login alert from a country I have never been to. Please help.",
    "Someone logged into my account from overseas last night and I do not recognise it.",
    "How long does standard shipping take to Brisbane? I am in the metro area.",
    "I live in a remote part of Western Australia. How many days will standard shipping take?",
    "How fast is express shipping?",
    "I chose standard shipping on order 51500 an hour ago but I want express. It is still Confirmed. Can you change it?",
    "Order 49320 has already shipped but I have moved house. Can you change the delivery address to 8 King Street, Hobart?",
    "Order 47222, worth 64 dollars, was dispatched 14 business days ago with standard shipping and has not arrived. Please send a replacement.",
    "My express order 48033, 55 dollars, was dispatched 6 business days ago and was guaranteed within 4. Nothing has arrived. Can I get a replacement?",
    "Order 52310 was dispatched 3 business days ago with standard shipping. When should it arrive?",
    "Order 46990, worth 240 dollars, was dispatched 15 business days ago and has not arrived.",
    "My package has not arrived.",
    "I was charged 32 dollars twice for order 51200. Please refund the duplicate.",
    "I cancelled order 50777 this morning but I was still charged 27 dollars. Please refund the charge.",
    "Which payment methods do you accept?",
    "I was charged 180 dollars for an order I never received a confirmation for. Please explain.",
    "There is a charge of 95 dollars on my card from you that is wrong. I was quoted 59 dollars.",
    "Please cancel my subscription at the end of this billing cycle. I am on the Plus plan.",
    "Can I pause my membership for 2 months this year without losing my loyalty points?",
    "I would like to upgrade from Basic to Plus. When does it take effect?",
    "Cancel my subscription now and refund me for this billing cycle. I paid 29 dollars on the 3rd.",
    "Can I get a copy of the invoice for order 44120 from March this year?",
    "I need an invoice from 3 years ago for order 31002. How do I get it?",
    "The tax on invoice 8821 looks wrong. It shows 14 dollars tax on a 60 dollar item and I think it should be 6 dollars.",
    "My blender from order 43100, bought 5 months ago, stopped turning on and the base smells burnt. I can send photos of the burnt base. Is it covered?",
    "The zipper on my 85 dollar backpack, delivered 3 months ago, came apart on its first use. I can send photos of the broken stitching. Please replace it.",
    "My speaker stopped working after I dropped it in the pool. I want a warranty replacement.",
    "My monitor has a dead pixel but I am not sure if it happened from how I carried it. I have no photo yet.",
    "Just wanted to say the new packaging is great, thank you!",
    "Suggestion: please add a dark mode to the mobile app.",
    "I am extremely unhappy with how my last order was handled. I want compensation, or I will post about it on social media.",
    "What are your phone support hours?",
    "This is the third time I have contacted you about order 48500. I want to speak to a manager.",
]


def load_done():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_done(done):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(done), f)


results = []   # (message, worked, status text)


def send(message):
    try:
        r = requests.post(URL, json={"message": message}, headers=HEADERS, timeout=300)
        try:
            status = r.json().get("status", "unknown")
        except Exception:
            status = "unknown"
        if r.status_code == 200:
            results.append((message, True, status))
        else:
            results.append((message, False, f"HTTP {r.status_code} {status}"))
    except Exception as error:
        results.append((message, False, f"no answer ({type(error).__name__})"))


# ---- setup ---------------------------------------------------------------
if not KEY:
    sys.exit("No API_KEY set. Type the $env:API_KEY line first (see the top of this file).")
try:
    requests.get(BASE + "/health", timeout=10)
except Exception:
    sys.exit(f"Cannot reach the server at {BASE}. Is it running, and is the address right?")

done = load_done()
todo = [m for m in TICKETS if m not in done]
random.shuffle(todo)   # a different random order every run
print(len(done), "already sent,", len(todo), "to send")

# ---- send in small batches ---------------------------------------------------
sent_this_run = Counter()
failed_in_a_row = 0
for start in range(0, len(todo), BATCH_SIZE):
    batch = todo[start:start + BATCH_SIZE]
    results.clear()
    threads = [threading.Thread(target=send, args=(m,)) for m in batch]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for message, worked, status in results:
        if worked:
            done.add(message)
            sent_this_run[status] += 1
        print(f"  {status:24} | {message[:70]}")
    save_done(done)

    succeeded = sum(1 for _, worked, _ in results if worked)
    print(f"Batch done: {min(start + BATCH_SIZE, len(todo))} of {len(todo)} sent, "
          f"{succeeded} of {len(batch)} succeeded")

    if results and succeeded == 0:
        failed_in_a_row += 1
        if failed_in_a_row >= MAX_FAILED_BATCHES:
            print("Stopping: batches keep failing (probably the Gemini quota). "
                  "Wait a while, then run the same command again - finished tickets are skipped.")
            break
        print("Whole batch failed - waiting an extra 90 seconds")
        time.sleep(90)
    else:
        failed_in_a_row = 0
    if start + BATCH_SIZE < len(todo):
        time.sleep(PAUSE_SECONDS)

print()
print(f"Sent so far: {len(done)} of {len(TICKETS)}")
print("Outcomes this run:", dict(sent_this_run))
if len(done) < len(TICKETS):
    print("Some tickets are still unsent. Run the same command again to finish them.")