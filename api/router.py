from fastapi import APIRouter, BackgroundTasks
from api.endpoints import (
    event_details
)

from agents.venue_searching_agent.utils import process_venue_search

router = APIRouter()

router.include_router(event_details.router)

@router.get("/")
def health_check(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_venue_search, "e57b1b63-f5e0-403b-aa1b-b16be5703dfa", True)
    return {"status": "ok"}