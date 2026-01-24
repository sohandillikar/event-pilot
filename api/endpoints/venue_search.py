from fastapi import APIRouter, Request

router = APIRouter()
PREFIX = "/venue_search"


@router.post(f"{PREFIX}/process")
async def process(request: Request):
    """Process the venue search request based on event ID."""
    payload = await request.json()
    event_id = payload.get("event_id")
    print(f"Will search for venues for event {event_id}")
    return {"status": "success"}