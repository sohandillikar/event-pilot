import os
from dotenv import load_dotenv
from fastapi import APIRouter, Request
import resend

load_dotenv()

router = APIRouter()
PREFIX = "/venue_search"

resend.api_key = os.getenv("RESEND_API_KEY")


@router.post(f"{PREFIX}/webhook")
async def webhook(request: Request):
    """Handle webhook requests from Resend."""
    payload = await request.json()

    if payload.get("type") == "email.received":
        email_params = {
            "from": f"Ava from EventPilot <ava@{os.getenv('RESEND_DOMAIN')}>",
            "to": payload.get("data").get("from"),
            "reply_to": f"ava@{os.getenv('RESEND_DOMAIN')}",
            "subject": payload.get("data").get("subject"),
            "text": "This is a response test.",
            "headers": {
                "In-Reply-To": payload.get("data").get("message_id"),
            }
        }
        # resend.Emails.send(email_params)
        print(email_params)
    
    return {"status": "success"}