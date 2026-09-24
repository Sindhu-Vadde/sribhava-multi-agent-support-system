import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from trace_logger import log_trace

load_dotenv()
gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

critic_decision_function = {
    "name": "critic_decision",
    "description": "Review a proposed decision on a support ticket and decide whether to approve it or override it to force escalation.",
    "parameters": {
        "type": "object",
        "properties": {
            "approved": {
                "type": "boolean",
                "description": "True if the proposed decision is safe and correct. False if it should be overridden."
            },
            "reasoning": {
                "type": "string",
                "description": "Explanation for why the decision was approved or overridden."
            }
        },
        "required": ["approved", "reasoning"]
    }
}


def critic_agent(message: str, policy_reasoning: str, proposed_decision: dict, ticket_id: int = None) -> dict:
    tools = types.Tool(function_declarations=[critic_decision_function])
    config = types.GenerateContentConfig(tools=[tools])

    prompt = f"""You are a safety reviewer for Sribhava Retail support decisions. Review the following proposed decision before it is allowed to execute.

Customer message: {message}
Policy reasoning: {policy_reasoning}
Proposed decision: {proposed_decision['decision']}
Proposed reasoning: {proposed_decision['reasoning']}

Your job is specifically to catch cases where 'auto_resolve' was chosen but shouldn't have been, given the policy's escalation rules. If the proposed decision is 'escalate', you should almost always approve it, since escalating too often is safer than not escalating enough. If the proposed decision is 'auto_resolve', check carefully whether the policy reasoning actually supports that being safe."""

    response = gemini_client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=config
    )

    function_call = response.candidates[0].content.parts[0].function_call
    review_result = dict(function_call.args)

    if ticket_id is not None:
        log_trace(ticket_id, "Critic", str(review_result["approved"]), review_result["reasoning"])

    return review_result


if __name__ == "__main__":
    from classifier_agent import classify_ticket
    from policy_agent import policy_agent

    test_message = "I want a refund of $250 for my damaged item"
    classification = classify_ticket(test_message)
    print("Classification:", classification)

    reasoning = policy_agent(test_message, classification)
    print("\nPolicy reasoning:", reasoning)

    fake_proposed_decision = {"decision": "auto_resolve", "reasoning": "Refund amount is under $300, auto-resolving."}
    print("\nProposed decision:", fake_proposed_decision)

    review = critic_agent(test_message, reasoning, fake_proposed_decision)
    print("\nCritic review:", review)