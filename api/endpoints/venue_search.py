from fastapi import APIRouter, Request

router = APIRouter()
PREFIX = "/venue_search"

@router.post(f"{PREFIX}/webhook")
async def webhook(request: Request):
    """Handle webhook requests from Resend."""
    payload = await request.json()
    print(payload)
    return {"status": "success"}