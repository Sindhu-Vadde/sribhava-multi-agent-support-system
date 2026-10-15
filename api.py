import asyncio
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from langgraph_pipeline import fail_over_to_human, run_ticket, server_params
from mcp_supervisor import McpSupervisor
from trace_logger import create_ticket, init_db

WAIT_FOR_TOOL_SERVER_SECONDS = 20

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str | None = Security(api_key_header)):
    expected = os.environ.get("API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="Server has no API key configured")
    if not key or not secrets.compare_digest(key, expected):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    supervisor = McpSupervisor(server_params)
    await supervisor.start()
    app.state.supervisor = supervisor
    yield
    await supervisor.stop()


app = FastAPI(lifespan=lifespan)


class Ticket(BaseModel):
    message: str


async def wait_for_tool_server(supervisor) -> bool:
    """True if the tool server is answering. If not, asks for a restart and waits a little."""
    if await supervisor.is_healthy():
        return True
    # If there is no connection at all, the supervisor is already reconnecting by itself.
    if supervisor.session is not None:
        supervisor.request_restart()
    for _ in range(WAIT_FOR_TOOL_SERVER_SECONDS * 2):
        await asyncio.sleep(0.5)
        if supervisor.session is not None and await supervisor.is_healthy():
            return True
    return False


def with_human_response(ticket_id, detail):
    return JSONResponse(
        status_code=503,
        content={"ticket_id": ticket_id, "status": "with_human", "detail": detail},
    )


@app.post("/submit_ticket", dependencies=[Depends(require_api_key)])
async def submit_ticket(ticket: Ticket, request: Request):
    supervisor = request.app.state.supervisor

    # 1. Tool server not available: do not lose the ticket, give it to a person.
    if not await wait_for_tool_server(supervisor):
        ticket_id = create_ticket(ticket.message)
        fail_over_to_human(
            ticket_id,
            "System failure: the tool server was not available, so a person needs to handle this ticket.",
        )
        return with_human_response(
            ticket_id, "Our system had a problem. A person will handle your ticket."
        )

    # 2. Normal path.
    try:
        ticket_id = await run_ticket(ticket.message, supervisor.session)
    except asyncio.TimeoutError as e:
        # run_ticket has already moved the ticket to the human queue.
        return with_human_response(
            getattr(e, "ticket_id", None),
            "Your ticket took too long to process. A person will handle it.",
        )
    except Exception as e:
        ticket_id = getattr(e, "ticket_id", None)
        # If the tool server died while working, ask for a restart and give the ticket to a person.
        if ticket_id is not None and not await supervisor.is_healthy():
            if supervisor.session is not None:
                supervisor.request_restart()
            fail_over_to_human(
                ticket_id,
                "System failure: the tool server stopped working while this ticket was being processed.",
            )
            return with_human_response(
                ticket_id, "Our system had a problem. A person will handle your ticket."
            )
        return JSONResponse(
            status_code=500,
            content={"ticket_id": ticket_id, "status": "error",
                     "detail": "The ticket could not be processed."},
        )

    return {"ticket_id": ticket_id, "status": "processed"}


@app.get("/")
async def root():
    return {"status": "running"}


@app.get("/health")
async def health(request: Request):
    supervisor = request.app.state.supervisor
    if await supervisor.is_healthy():
        return {"status": "ok", "mcp": "up", "restarts": supervisor.restart_count}
    return JSONResponse(
        status_code=503,
        content={"status": "degraded", "mcp": "down", "restarts": supervisor.restart_count},
    )