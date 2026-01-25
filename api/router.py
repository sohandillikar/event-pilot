from fastapi import APIRouter
from api.endpoints import (
    event_details
)

router = APIRouter()

router.include_router(event_details.router)

@router.get("/")
def health_check():
    return {"status": "ok"}