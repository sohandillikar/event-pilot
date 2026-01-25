from fastapi import APIRouter
from api.endpoints import (
    event_details
)

from agents.venue_searching_agent.utils import process_venue_search

router = APIRouter()

router.include_router(event_details.router)

@router.get("/")
def health_check():
    process_venue_search("e57b1b63-f5e0-403b-aa1b-b16be5703dfa")
    return {"status": "ok"}