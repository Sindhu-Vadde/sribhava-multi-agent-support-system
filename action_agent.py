import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv
from trace_logger import log_trace, get_usage

load_dotenv()
gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

decide_action_function = {
    "name": "decide_action",
    "description": "Decide whether a support ticket can be auto-resolved or must be escalated to a human.",
    "parameters": {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["auto_resolve", "escalate"],
                "description": "Whether to auto-resolve the ticket or escalate it to a human."
            },
            "reasoning": {
                "type": "string",
                "description": "Explanation for the decision, including any missing information that led to escalation."
            }
        },
        "required": ["decision", "reasoning"]
    }
}


def decide_action(message: str, classification: dict, policy_reasoning: str, ticket_id: int = None) -> dict:
    """Decides only. Nothing is executed here, so the Critic Agent can review first."""
    start = time.perf_counter()

    tools = types.Tool(function_declarations=[decide_action_function])
    config = types.GenerateContentConfig(tools=[tools])

    prompt = f"""You are the final decision-making agent for Sribhava Retail support tickets.

Customer message: {message}
Classification: {classification['category']} / {classification['intent']}
Policy reasoning: {policy_reasoning}

Decide whether this ticket can be safely auto-resolved, or must be escalated to a human.

IMPORTANT: If the message does not contain enough specific information (such as order value, exact timing, or other details needed to confidently apply the policy's rules), you MUST escalate rather than guess. Only choose auto_resolve if you are confident, based on concrete details actually present in the message, that no escalation rule applies."""

    response = gemini_client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=config
    )

    function_call = response.candidates[0].content.parts[0].function_call
    decision_result = dict(function_call.args)

    latency_ms = int((time.perf_counter() - start) * 1000)
    input_tokens, output_tokens = get_usage(response)

    if ticket_id is not None:
        log_trace(
            ticket_id,
            "Action",
            decision_result["decision"],
            decision_result["reasoning"],
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

    return decision_result


async def execute_decision(ticket_id: int, decision_result: dict, session) -> str:
    """Carries out an already-approved decision through the shared MCP session."""
    if decision_result["decision"] == "escalate":
        result = await session.call_tool(
            "escalate_to_human",
            {"ticket_id": ticket_id, "reason": decision_result["reasoning"]}
        )
    else:
        result = await session.call_tool(
            "update_ticket",
            {"ticket_id": ticket_id, "status": "auto_resolved", "agent_reasoning": decision_result["reasoning"]}
        )

    return result.content[0].text