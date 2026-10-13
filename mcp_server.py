import time
T0 = time.perf_counter()

import sys
import sqlite3
from mcp.server.mcpserver import MCPServer
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

print(f"[startup] imports finished: {time.perf_counter() - T0:.1f}s", file=sys.stderr)

mcp = MCPServer("sribhava-support-tools")

client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(
        chroma_api_impl="chromadb.api.segment.SegmentAPI",
        anonymized_telemetry=False
    )
)
collection = client.get_or_create_collection(name="sribhava_policies")

print(f"[startup] chromadb ready: {time.perf_counter() - T0:.1f}s", file=sys.stderr)

model = SentenceTransformer("all-MiniLM-L6-v2")

print(f"[startup] model loaded: {time.perf_counter() - T0:.1f}s", file=sys.stderr)


@mcp.tool()
def search_policy(query: str) -> str:
    """Search Sribhava Retail's policy documents for the most relevant policy given a customer query."""
    query_embedding = model.encode([query]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=1)

    title = results["metadatas"][0][0]["title"]
    content = results["documents"][0][0]

    return f"Policy: {title}\n{content}"


@mcp.tool()
def update_ticket(ticket_id: int, status: str, agent_reasoning: str) -> str:
    """Update a support ticket's status and record the reasoning behind the decision. Status should be one of: 'auto_resolved', 'pending_human_review'."""
    conn = sqlite3.connect("tickets.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE tickets SET status = ?, agent_reasoning = ? WHERE id = ?",
        (status, agent_reasoning, ticket_id)
    )
    conn.commit()
    rows_changed = cursor.rowcount
    conn.close()

    if rows_changed == 0:
        return f"No ticket found with id {ticket_id}"
    return f"Ticket {ticket_id} updated to status '{status}'"


@mcp.tool()
def escalate_to_human(ticket_id: int, reason: str) -> str:
    """Flag a ticket as requiring human review, with the reason why it couldn't be auto-resolved."""
    conn = sqlite3.connect("tickets.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE tickets SET status = 'pending_human_review', agent_reasoning = ? WHERE id = ?",
        (reason, ticket_id)
    )
    conn.commit()
    rows_changed = cursor.rowcount
    conn.close()

    if rows_changed == 0:
        return f"No ticket found with id {ticket_id}"
    return f"Ticket {ticket_id} escalated to human review: {reason}"


if __name__ == "__main__":
    # `python mcp_server.py test` runs the three tools directly once, then exits.
    # `python mcp_server.py` starts the real, long-running server.
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("\n--- Testing search_policy ---")
        print(search_policy("I want to cancel my order"))

        print("\n--- Testing update_ticket ---")
        print(update_ticket(1, "auto_resolved", "Order was within the 60-minute cancellation window, auto-approved."))

        print("\n--- Testing escalate_to_human ---")
        print(escalate_to_human(1, "Refund amount exceeds $300 threshold, requires manual review."))
    else:
        mcp.run()