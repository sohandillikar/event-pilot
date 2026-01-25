import os
from dotenv import load_dotenv
import json
import logging

import resend
import markdown
from datetime import datetime

from supabase import create_client
from .agent import search_nearby_venues, get_venue_pricing
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

load_dotenv()

logger = logging.getLogger(__name__)
supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY"))
resend.api_key = os.getenv("RESEND_API_KEY")

STATE_TO_CODE = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY"
}


def process_venue_search(event_id: str, send_email: bool = False):
    logger.info(f"[FUNCTION CALL] - process_venue_search(event_id={event_id}, send_email={send_email})")

    response = supabase_client.table("events").select("*").eq("id", event_id).execute()
    event = response.data[0]
    
    city = event.get("city")
    state = event.get("state")
    state_code = STATE_TO_CODE.get(state.lower(), state)
    
    venues = search_nearby_venues.invoke({"city": city, "state": state_code, "venue_type": event.get("venue_type")})

    venues_to_insert = []
    for venue in venues:
        pricing = get_venue_pricing.invoke({"name": venue.get("name"), "city": city, "state": state_code})
        venues_to_insert.append({
            "event_id": event_id,
            "google_place_id": venue.get("place_id"),
            "name": venue.get("name"),
            "address": venue.get("address"),
            "phone": venue.get("phone"),
            "website": venue.get("website"),
            "rating": venue.get("rating"),
            "rating_count": venue.get("rating_count"),
            "latitude": venue.get("location", {}).get("lat"),
            "longitude": venue.get("location", {}).get("lng"),
            "google_types": venue.get("types", []),
            "pricing": pricing
        })

    if venues_to_insert:
        supabase_client.table("venues").insert(venues_to_insert).execute()

    if send_email:
        email_customer_about_venues(event_id)


def generate_email_about_venues(data: dict, to_email: str) -> dict:
    logger.info(f"[FUNCTION CALL] - generate_email_about_venues(data=..., to_email={to_email})")

    prompt_path = os.path.join(os.path.dirname(__file__), "email_notification_system_prompt.md")
    with open(prompt_path, "r") as input_file:
        SYSTEM_PROMPT = input_file.read()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{data_json}")
    ])
    llm = ChatOpenAI(model="gpt-4o-mini")
    chain = prompt | llm
    response = chain.invoke({"data_json": json.dumps(data)})
    email_content = markdown.markdown(response.content)

    start_date_formatted = datetime.strptime(data.get("event").get("start_date"), "%Y-%m-%d").strftime("%b %d")
    subject_line = f"Venue Recommendations for Your Upcoming Event on {start_date_formatted}"

    return {
        "from": "Ava from EventPilot <ava@aggiebuilds.com>",
        "to": to_email,
        "subject": subject_line,
        "html": email_content
    }


def email_customer_about_venues(event_id: str):
    logger.info(f"[FUNCTION CALL] - email_customer_about_venues(event_id={event_id})")

    event = supabase_client.table("events").select("*").eq("id", event_id).execute().data[0]
    customer = supabase_client.table("users").select("*").eq("id", event.get("user_id")).execute().data[0]
    venues = supabase_client.table("venues").select("*").eq("event_id", event_id).execute().data
    
    data = {
        "customer": {"name": customer.get("name")},
        "event": {
            "start_date": event.get("start_date"),
            "end_date": event.get("end_date"),
            "number_of_attendees": event.get("number_of_attendees"),
            "venue_type": event.get("venue_type"),
            "city": event.get("city"),
            "state": event.get("state"),
            "budget_min": event.get("budget_min"),
            "budget_max": event.get("budget_max")
        },
        "venues": [{
            "name": v.get("name"),
            "address": v.get("address"),
            "website": v.get("website"),
            "rating": f"{v.get('rating')}/5.0",
            "rating_count": v.get("rating_count"),
            "pricing": v.get("pricing")
        } for v in venues]
    }

    # TODO: Change to customer.get("email") for production
    email_params = generate_email_about_venues(data, "sohanyt.main@gmail.com")
    return resend.Emails.send(email_params)