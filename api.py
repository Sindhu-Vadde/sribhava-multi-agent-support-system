import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from langgraph_pipeline import run_ticket, server_params
from trace_logger import log_trace


@asynccontextmanager
async def lifespan(app: FastAPI):
    start = time.perf_counter()
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            startup_ms = int((time.perf_counter() - start) * 1000)
            print(f"MCP server started once, in {startup_ms} ms")
            log_trace(None, "MCP startup", "server_ready",
                      "One-time start when the API launched",
                      latency_ms=startup_ms)
            app.state.session = session
            yield


app = FastAPI(lifespan=lifespan)


class Ticket(BaseModel):
    message: str


@app.post("/submit_ticket")
async def submit_ticket(ticket: Ticket):
    ticket_id = await run_ticket(ticket.message, app.state.session)
    return {"ticket_id": ticket_id, "status": "processed"}


@app.get("/")
def health_check():
    return {"status": "running"}