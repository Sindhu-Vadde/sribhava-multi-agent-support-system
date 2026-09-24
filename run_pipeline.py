import asyncio
import sqlite3
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from trace_logger import create_ticket
from classifier_agent import classify_ticket
from policy_agent import policy_agent
from action_agent import decide_action, execute_decision
from critic_agent import critic_agent

server_params = StdioServerParameters(
    command="python",
    args=["mcp_server.py"]
)


async def run_full_pipeline(message: str):
    ticket_id = create_ticket(message)
    print(f"\n=== Created ticket #{ticket_id} ===")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                classification = classify_ticket(message, ticket_id=ticket_id)
                print("\nClassification:", classification)

                reasoning = await policy_agent(message, classification, session, ticket_id=ticket_id)
                print("\nPolicy reasoning:", reasoning)

                proposed = decide_action(message, classification, reasoning, ticket_id=ticket_id)
                print("\nProposed decision:", proposed)

                review = critic_agent(message, reasoning, proposed, ticket_id=ticket_id)
                print("\nCritic review:", review)

                if review["approved"]:
                    final_decision = proposed
                    print("\nCritic approved. Executing original decision.")
                else:
                    final_decision = {"decision": "escalate", "reasoning": f"Overridden by Critic Agent: {review['reasoning']}"}
                    print("\nCritic overrode the decision. Forcing escalation instead.")

                result = await execute_decision(ticket_id, final_decision, session)
                print("\nFinal outcome:", result)

    except Exception as e:
        print(f"\nPipeline failed for ticket #{ticket_id}: {e}")
        conn = sqlite3.connect("tickets.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE tickets SET status = 'error' WHERE id = ?", (ticket_id,))
        conn.commit()
        conn.close()
        raise

    return ticket_id


if __name__ == "__main__":
    test_message = "I want a refund of $250 for my damaged item"
    asyncio.run(run_full_pipeline(test_message))