import os
import json
import sqlite3
from google import genai
from google.genai import types
from dotenv import load_dotenv
from trace_logger import log_trace

load_dotenv()
gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

classify_ticket_function = {
    "name": "classify_ticket",
    "description": "Classify a customer support ticket into a category and intent.",
    "parameters": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "The broad category of the ticket, e.g. ORDER, REFUND, ACCOUNT, PAYMENT, INVOICE, SHIPPING, DELIVERY, SUBSCRIPTION, CONTACT, FEEDBACK"
            },
            "intent": {
                "type": "string",
                "description": "The specific intent within that category, e.g. cancel_order, check_refund_policy"
            },
            "reasoning": {
                "type": "string",
                "description": "A brief explanation of why this category and intent were chosen."
            }
        },
        "required": ["category", "intent", "reasoning"]
    }
}

def classify_ticket(message: str, ticket_id: int = None) -> dict:
    tools = types.Tool(function_declarations=[classify_ticket_function])
    config = types.GenerateContentConfig(tools=[tools])

    prompt = f"""You are a support ticket classifier for Sribhava Retail. Classify the following customer message by calling the classify_ticket function.

Important distinctions between similar categories:
- CANCEL is specifically for questions about cancellation fees, termination penalties, or early exit charges — NOT general subscription management.
- SUBSCRIPTION is for managing an active subscription (pausing, upgrading, downgrading, newsletter preferences) — not questions about the cost of leaving it.
- DELIVERY is about the shipment's actual transit status (where is it, when will it arrive, did it arrive) — SHIPPING is about shipping methods, costs, or address changes before dispatch.
- FEEDBACK is for complaints, reviews, or opinions about the company — CONTACT is for questions about HOW to reach support, not about lodging a complaint itself.


Customer message: {message}"""

    response = gemini_client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=config
    )

    function_call = response.candidates[0].content.parts[0].function_call
    result = dict(function_call.args)

    if ticket_id is not None:
        log_trace(ticket_id, "Classifier", f"{result['category']}/{result['intent']}", result['reasoning'])

        conn = sqlite3.connect("tickets.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tickets SET category = ?, intent = ? WHERE id = ?",
            (result['category'], result['intent'], ticket_id)
        )
        conn.commit()
        conn.close()

    return result


if __name__ == "__main__":
    test_messages = [
        "I want to cancel my order, it hasn't shipped yet",
        "My package never arrived and it's been 2 weeks",
        "Can I pause my subscription for a few months?"
    ]

    for msg in test_messages:
        result = classify_ticket(msg)
        print("\nMessage:", msg)
        print(json.dumps(result, indent=2))