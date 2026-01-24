from fastapi import APIRouter
from api.endpoints import (
    event_details,
    venue_search
)

router = APIRouter()

router.include_router(event_details.router)
router.include_router(venue_search.router)

@router.get("/")
def health_check():
    return {"status": "ok"}