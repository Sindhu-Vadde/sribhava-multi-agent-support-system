from fastapi import FastAPI
from pydantic import BaseModel
from run_pipeline import run_full_pipeline

app = FastAPI()

class Ticket(BaseModel):
    message: str

@app.post("/submit_ticket")
async def submit_ticket(ticket: Ticket):
    ticket_id = await run_full_pipeline(ticket.message)
    return {"ticket_id": ticket_id, "status": "processed"}

@app.get("/")
def health_check():
    return {"status": "running"}