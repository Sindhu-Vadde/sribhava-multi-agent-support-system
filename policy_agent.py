import asyncio
import os
import time
from google import genai
from dotenv import load_dotenv
from trace_logger import log_trace, get_usage
from gemini_call import generate_with_retry

load_dotenv()
gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


async def policy_agent(message: str, classification: dict, session, ticket_id: int = None) -> str:
    start = time.perf_counter()

    query = f"{classification['category']} {classification['intent']}"

    # A real MCP protocol call to the already-open server session
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

    # Run in a separate thread, so a retry wait never freezes the whole API.
    response = await asyncio.to_thread(
        generate_with_retry,
        gemini_client,
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=None
    )

    result_text = response.text

    latency_ms = int((time.perf_counter() - start) * 1000)
    input_tokens, output_tokens = get_usage(response)

    if ticket_id is not None:
        log_trace(
            ticket_id,
            "Policy",
            "reasoning_generated",
            result_text,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

    return result_text