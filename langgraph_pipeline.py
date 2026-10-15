import asyncio
import os
import sqlite3
import time
from typing import TypedDict
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from langgraph.graph import StateGraph, END
from trace_logger import create_ticket, log_trace
from classifier_agent import classify_ticket
from policy_agent import policy_agent
from action_agent import decide_action, execute_decision
from critic_agent import critic_agent

server_params = StdioServerParameters(command="python", args=["mcp_server.py"])

# If one ticket takes longer than this, we stop waiting and hand it to a human.
PIPELINE_TIMEOUT_SECONDS = float(os.environ.get("PIPELINE_TIMEOUT_SECONDS", "120"))


class PipelineState(TypedDict):
    message: str
    ticket_id: int
    classification: dict
    reasoning: str
    proposed_decision: dict
    critic_review: dict
    final_decision: dict
    result: str


def route_after_classify(state):
    """A fixed rule, not a model decision: unclassifiable tickets always go to a human."""
    category = str(state["classification"].get("category", "")).upper()
    if category == "UNCLASSIFIABLE":
        return "escalate_unclassified"
    return "policy"


def build_graph(session):
    def classify_node(state):
        return {"classification": classify_ticket(state["message"], ticket_id=state["ticket_id"])}

    async def policy_node(state):
        reasoning = await policy_agent(
            state["message"], state["classification"], session, ticket_id=state["ticket_id"]
        )
        return {"reasoning": reasoning}

    def action_node(state):
        return {"proposed_decision": decide_action(
            state["message"], state["classification"], state["reasoning"], ticket_id=state["ticket_id"]
        )}

    def critic_node(state):
        return {"critic_review": critic_agent(
            state["message"], state["reasoning"], state["proposed_decision"], ticket_id=state["ticket_id"]
        )}

    async def execute_node(state):
        if state["critic_review"]["approved"]:
            final_decision = state["proposed_decision"]
        else:
            final_decision = {
                "decision": "escalate",
                "reasoning": f"Overridden by Critic Agent: {state['critic_review']['reasoning']}",
            }
        result = await execute_decision(state["ticket_id"], final_decision, session)
        return {"final_decision": final_decision, "result": result}

    async def escalate_unclassified_node(state):
        final_decision = {
            "decision": "escalate",
            "reasoning": "Escalated by rule: the Classifier could not find a real support request in this message.",
        }
        log_trace(state["ticket_id"], "Rule", "escalate", final_decision["reasoning"])
        result = await execute_decision(state["ticket_id"], final_decision, session)
        return {"final_decision": final_decision, "result": result}

    graph = StateGraph(PipelineState)
    graph.add_node("classify", classify_node)
    graph.add_node("policy", policy_node)
    graph.add_node("action", action_node)
    graph.add_node("critic", critic_node)
    graph.add_node("execute", execute_node)
    graph.add_node("escalate_unclassified", escalate_unclassified_node)

    graph.set_entry_point("classify")
    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {"policy": "policy", "escalate_unclassified": "escalate_unclassified"},
    )
    graph.add_edge("policy", "action")
    graph.add_edge("action", "critic")
    graph.add_edge("critic", "execute")
    graph.add_edge("execute", END)
    graph.add_edge("escalate_unclassified", END)

    return graph.compile()


def fail_over_to_human(ticket_id: int, reason: str):
    """Sends a ticket to the human review queue without using the MCP server.
    Writes straight to the database, so it still works if the tool server is stuck.
    Only touches a ticket that is still 'open', so a finished ticket is never overwritten."""
    conn = sqlite3.connect("tickets.db")
    cur = conn.cursor()
    cur.execute(
        "UPDATE tickets SET status = 'pending_human_review', agent_reasoning = ? "
        "WHERE id = ? AND status = 'open'",
        (reason, ticket_id),
    )
    changed = cur.rowcount
    conn.commit()
    conn.close()
    if changed:
        log_trace(ticket_id, "Pipeline", "failover", reason)
    return bool(changed)


async def process_ticket(message: str, session, ticket_id: int):
    """The actual work for one ticket: runs the agents in order."""
    pipeline_start = time.perf_counter()
    app = build_graph(session)
    final_state = await app.ainvoke({"message": message, "ticket_id": ticket_id})

    print("\nClassification:", final_state.get("classification"))
    if "reasoning" in final_state:
        print("\nPolicy reasoning:", final_state["reasoning"])
        print("\nProposed decision:", final_state.get("proposed_decision"))
        print("\nCritic review:", final_state.get("critic_review"))
    else:
        print("\n(Escalated by rule - the other agents were skipped.)")
    print("\nFinal outcome:", final_state.get("result"))

    total_ms = int((time.perf_counter() - pipeline_start) * 1000)
    log_trace(ticket_id, "Pipeline", "completed",
              "Time from ticket created to finished, with the MCP server already running",
              latency_ms=total_ms)


async def run_ticket(message: str, session):
    """Processes one ticket using an MCP session that is already open.
    If it takes too long, the ticket goes to a human instead of hanging."""
    ticket_id = create_ticket(message)
    print(f"\n=== Created ticket #{ticket_id} ===")

    try:
        await asyncio.wait_for(
            process_ticket(message, session, ticket_id),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        reason = (f"System failure: processing took longer than "
                  f"{PIPELINE_TIMEOUT_SECONDS:g} seconds, so a person needs to handle this ticket.")
        print(f"\nTicket #{ticket_id} timed out - sent to a human")
        fail_over_to_human(ticket_id, reason)
        raise
    except Exception as e:
        print(f"\nPipeline failed for ticket #{ticket_id}: {e}")
        conn = sqlite3.connect("tickets.db")
        cur = conn.cursor()
        cur.execute("UPDATE tickets SET status = 'error' WHERE id = ?", (ticket_id,))
        conn.commit()
        conn.close()
        raise

    return ticket_id


async def run_full_pipeline(message: str):
    """Starts its own MCP server for this one ticket, then processes it."""
    startup_start = time.perf_counter()
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            startup_ms = int((time.perf_counter() - startup_start) * 1000)
            print(f"\nMCP server started in {startup_ms} ms")

            ticket_id = await run_ticket(message, session)
            log_trace(ticket_id, "MCP startup", "server_ready",
                      "Time to start the MCP server and open the session",
                      latency_ms=startup_ms)
    return ticket_id


if __name__ == "__main__":
    asyncio.run(run_full_pipeline("asdf qwerty zxcv"))