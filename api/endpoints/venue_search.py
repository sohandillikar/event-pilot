import os
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from agents.venue_searching_agent.utils import create_email_response
from supabase import create_client
import resend
import logging

load_dotenv()

router = APIRouter()
PREFIX = "/venue_search"

logger = logging.getLogger(__name__)
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY"))
resend.api_key = os.getenv("RESEND_API_KEY")


@router.post(f"{PREFIX}/webhook")
async def webhook(request: Request):
    """Handle webhook requests from Resend."""
    payload = await request.json()
    print(payload)

    if payload.get("type") == "email.received":
        # Extract email data
        to_email = payload.get("data").get("to")[0]
        from_email = payload.get("data").get("from")
        subject = payload.get("data").get("subject")
        try:
            event_id = to_email.split("event+")[1].split("@")[0]
        except Exception as e:
            message = f"Error extracting event ID from email: {to_email} - {e}"
            logger.error(message)
            return {"status": "error", "message": message}

        # Get email data from Resend
        email_data = resend.EmailsReceiving.get(payload.get("data").get("email_id"))

        # Insert email data into Supabase
        supabase.table("email_messages").insert({
            "event_id": event_id,
            "resend_id": payload.get("data").get("email_id"),
            "from_email": from_email,
            "to_email": to_email,
            "subject": subject,
            "body_text": email_data.get("text"),
            "body_html": email_data.get("html")
        }).execute()

        # Create email response
        text, html = create_email_response(event_id)

        # Send email response
        email_params = {
            "from": f"Ava from EventPilot <{to_email}>",
            "to": from_email,
            "reply_to": to_email,
            "subject": subject,
            "html": html,
            "headers": {
                "In-Reply-To": payload.get("data").get("message_id"),
            }
        }
        email_id = resend.Emails.send(email_params).get("id")

        # Insert email response data into Supabase
        supabase.table("email_messages").insert({
            "event_id": event_id,
            "resend_id": email_id,
            "from_email": to_email,
            "to_email": from_email,
            "subject": payload.get("data").get("subject"),
            "body_text": text,
            "body_html": html
        }).execute()
    
    return {"status": "success"}