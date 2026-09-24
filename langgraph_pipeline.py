import asyncio
import sqlite3
from typing import TypedDict
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from langgraph.graph import StateGraph, END
from trace_logger import create_ticket
from classifier_agent import classify_ticket
from policy_agent import policy_agent
from action_agent import decide_action, execute_decision
from critic_agent import critic_agent

server_params = StdioServerParameters(
    command="python",
    args=["mcp_server.py"]
)


class PipelineState(TypedDict):
    message: str
    ticket_id: int
    classification: dict
    reasoning: str
    proposed_decision: dict
    critic_review: dict
    final_decision: dict
    result: str


def build_graph(session):
    def classify_node(state):
        classification = classify_ticket(state["message"], ticket_id=state["ticket_id"])
        return {"classification": classification}

    async def policy_node(state):
        reasoning = await policy_agent(state["message"], state["classification"], session, ticket_id=state["ticket_id"])
        return {"reasoning": reasoning}

    def action_node(state):
        proposed = decide_action(state["message"], state["classification"], state["reasoning"], ticket_id=state["ticket_id"])
        return {"proposed_decision": proposed}

    def critic_node(state):
        review = critic_agent(state["message"], state["reasoning"], state["proposed_decision"], ticket_id=state["ticket_id"])
        return {"critic_review": review}

    async def execute_node(state):
        if state["critic_review"]["approved"]:
            final_decision = state["proposed_decision"]
        else:
            final_decision = {"decision": "escalate", "reasoning": f"Overridden by Critic Agent: {state['critic_review']['reasoning']}"}

        result = await execute_decision(state["ticket_id"], final_decision, session)
        return {"final_decision": final_decision, "result": result}

    graph = StateGraph(PipelineState)

    graph.add_node("classify", classify_node)
    graph.add_node("policy", policy_node)
    graph.add_node("action", action_node)
    graph.add_node("critic", critic_node)
    graph.add_node("execute", execute_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "policy")
    graph.add_edge("policy", "action")
    graph.add_edge("action", "critic")
    graph.add_edge("critic", "execute")
    graph.add_edge("execute", END)

    return graph.compile()


async def run_full_pipeline(message: str):
    ticket_id = create_ticket(message)
    print(f"\n=== Created ticket #{ticket_id} ===")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                app = build_graph(session)

                initial_state = {"message": message, "ticket_id": ticket_id}
                final_state = await app.ainvoke(initial_state)

                print("\nClassification:", final_state["classification"])
                print("\nPolicy reasoning:", final_state["reasoning"])
                print("\nProposed decision:", final_state["proposed_decision"])
                print("\nCritic review:", final_state["critic_review"])
                print("\nFinal outcome:", final_state["result"])

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