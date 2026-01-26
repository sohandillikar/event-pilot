import os
from dotenv import load_dotenv
import json
import logging

import resend
import markdown
from datetime import datetime

from supabase import create_client
from .agent import (    # Add a dot here to import the agent
    search_nearby_venues,
    get_venue_pricing,
    negotiate_with_venue,
    web_search,
    trim_messages_middleware,
)

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
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


def generate_email_about_venues(data: dict, event_id: str, to_email: str) -> dict:
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
        "from": f"Andrew from EventPilot <andrew@{os.getenv('RESEND_DOMAIN')}>",
        "to": to_email,
        "reply_to": f"event+{event_id}@{os.getenv('RESEND_DOMAIN')}",
        "subject": subject_line,
        "html": email_content,
        "text": response.content
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
    email_params = generate_email_about_venues(data, event_id, "sohanyt.main@gmail.com")

    # Remove text from email params and get from email
    email_body_text = email_params.pop("text")
    from_email = email_params.get("from").split("<")[1].split(">")[0]

    # Send email and insert email message into Supabase
    email_id = resend.Emails.send(email_params).get("id")
    supabase_client.table("email_messages").insert({
        "event_id": event_id,
        "resend_id": email_id,
        "from_email": from_email,
        "to_email": email_params.get("to"),
        "subject": email_params.get("subject"),
        "body_text": email_body_text,
        "body_html": email_params.get("html")
    }).execute()


def create_email_response(event_id: str):
    logger.info(f"[FUNCTION CALL] - create_email_response(event_id={event_id})")

    emails = supabase_client.table("email_messages").select("*").eq("event_id", event_id).order("created_at").execute().data
    messages_for_agent = []

    for email in emails:
        outbound = email.get("from_email", "").endswith(os.getenv("RESEND_DOMAIN"))
        content = email.get("body_text", email.get("body_html", ""))
        if outbound:
            messages_for_agent.append(AIMessage(content=content))
        else:
            messages_for_agent.append(HumanMessage(content=content))

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
            "id": v.get("id"),
            "name": v.get("name"),
            "address": v.get("address"),
            "website": v.get("website"),
            "rating": f"{v.get('rating')}/5.0",
            "rating_count": v.get("rating_count"),
            "pricing": v.get("pricing")
        } for v in venues]
    }

    prompt_path = os.path.join(os.path.dirname(__file__), "email_response_system_prompt.md")
    with open(prompt_path, "r") as input_file:
        SYSTEM_PROMPT = input_file.read().replace("{{data}}", json.dumps(data))

    agent = create_agent(
        model="openai:gpt-4o-mini",
        system_prompt=SYSTEM_PROMPT,
        tools=[search_nearby_venues, get_venue_pricing, negotiate_with_venue, web_search],
        middleware=[trim_messages_middleware]
    )

    response = agent.invoke({"messages": messages_for_agent})
    response_text = response["messages"][-1].content
    response_html = markdown.markdown(response_text)

    return response_text, response_html