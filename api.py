import asyncio
import os
import secrets
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from mcp import ClientSession
from mcp.client.stdio import stdio_client

from langgraph_pipeline import run_ticket, server_params
from trace_logger import log_trace

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(supplied: str | None = Security(api_key_header)):
    """Reject any request that does not carry the secret key.

    The key is read at request time. If no key is configured the API refuses
    to serve tickets (fails closed) instead of running open to everyone.
    """
    expected = os.environ.get("API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Server has no API_KEY configured")
    if not supplied or not secrets.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")


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


@app.post("/submit_ticket", dependencies=[Depends(require_api_key)])
async def submit_ticket(ticket: Ticket):
    ticket_id = await run_ticket(ticket.message, app.state.session)
    return {"ticket_id": ticket_id, "status": "processed"}


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/health")
async def health():
    """Public, no key: lets a cloud platform check the app and its tool server."""
    session = getattr(app.state, "session", None)
    if session is None:
        return JSONResponse({"status": "unavailable", "mcp": "not started"}, status_code=503)
    try:
        await asyncio.wait_for(session.list_tools(), timeout=5)
    except Exception:
        return JSONResponse({"status": "unavailable", "mcp": "not responding"}, status_code=503)
    return {"status": "ok", "mcp": "up"}