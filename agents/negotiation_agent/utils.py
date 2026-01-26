import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY"))

def start_negotiation(venue_id: str):
    supabase_client.table("venues").update({
        "status": "negotiating"
    }).eq("id", venue_id).execute()