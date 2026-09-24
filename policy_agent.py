import os
from google import genai
from dotenv import load_dotenv
from trace_logger import log_trace

load_dotenv()
gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

async def policy_agent(message: str, classification: dict, session, ticket_id: int = None) -> str:
    query = f"{classification['category']} {classification['intent']}"

    result = await session.call_tool("search_policy", {"query": query})
    policy_text = result.content[0].text

    print("\n--- Retrieved policy (raw) ---")
    print(policy_text)
    print("--- End retrieved policy ---\n")

    prompt = f"""You are a policy reasoning agent for Sribhava Retail. A customer ticket has been classified as:
Category: {classification['category']}
Intent: {classification['intent']}

The customer's original message was: {message}

The relevant policy found is:
{policy_text}

Explain, in 2-3 sentences, what this policy means for this specific ticket, and whether any escalation rule applies. Use any specific details present in the customer's original message (such as dollar amounts, item conditions, or reasons given) to make as concrete a determination as possible."""

    response = gemini_client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    result_text = response.text

    if ticket_id is not None:
        log_trace(ticket_id, "Policy", "reasoning_generated", result_text)

    return result_text