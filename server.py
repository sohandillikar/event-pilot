import os
import time
from dotenv import load_dotenv
from datetime import datetime, timezone

from bson.objectid import ObjectId

import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

from vapi import Vapi
from agents.venue_searching_agent.venue_searching_agent import VenueSearchingAgent

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mongo_client = MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
mongo_client.admin.command("ping")
events_db = mongo_client["events_db"]
events_collection = events_db["events"]

vapi_client = Vapi(token=os.getenv("VAPI_API_KEY"))


def negotiate_with_venues(venues: list[dict]):
    """Negotiate with the venues for the given event."""
    for i, venue in enumerate(venues):
        print(f"Negotiating with venue {venue['name']} at {venue['contact_phone_number']} ({i+1}/{len(venues)})")
        call = vapi_client.calls.create(
            assistant_id=os.getenv("NEGOTIATION_ASSISTANT_ID"),
            phone_number_id=os.getenv("VAPI_PHONE_NUMBER_ID"),
            customer={"number": venue["contact_phone_number"]},
        )
        print(f"Call created - {call.id}")
        time.sleep(1)
        return # TODO: Remove this for production


def search_venues(event_id: str):
    """Search for venues that best suit an event and save them to MongoDB Atlas."""
    print(f"Searching for venues for event {event_id}")
    agent = VenueSearchingAgent(event_id)
    venues = agent.search_venues()
    agent.save_venues(venues)
    venues = agent.extract_venue_contact_info()
    agent.save_venues(venues)
    print(f"Found {len(venues)} venues for event {event_id}")

    negotiate_with_venues(venues)


@app.post("/events/create")
async def create_event(request: Request, background_tasks: BackgroundTasks):
    """Create and save a new event in MongoDB Atlas."""
    payload = await request.json()
    tool_call = payload.get("message", {}).get("toolCalls", [{}])[0]
    tool_call_id = tool_call.get("id")
    
    event_details = tool_call.get("function", {}).get("arguments")
    event_details["created_at"] = datetime.now(timezone.utc)
    event_details["customer_phone"] = payload["message"]["customer"]["number"]
    result = events_collection.insert_one(event_details)
    event_id = str(result.inserted_id)

    background_tasks.add_task(search_venues, event_id)

    result = {"status": "success", "event_id": event_id}
    return {"results": [{"toolCallId": tool_call_id, "result": result}]}


@app.post("/get_negotiation_context")
async def get_negotiation_context(request: Request):
    """Returns the event details and the venue details for the given venue contact phone number."""
    payload = await request.json()
    tool_call = payload.get("message", {}).get("toolCalls", [{}])[0]
    tool_call_id = tool_call.get("id")
    recipient_phone = payload["message"]["customer"]["number"]
    
    event = events_collection.find_one({
        "venues.contact_phone_number": recipient_phone
    })

    print(event)
    
    matching_venue = None
    for venue in event.get("venues", []):
        if venue.get("contact_phone_number") == recipient_phone:
            matching_venue = venue
            break

    del event["venues"]
    
    result = {
        "status": "success",
        "event_details": event,
        "venue_details": matching_venue
    }

    print(result)

    return {"results": [{"toolCallId": tool_call_id, "result": result}]}


@app.post("/save_negotiation_result")
async def save_negotiation_result(request: Request):
    """Saves the negotiation result to the database."""
    payload = await request.json()
    tool_call = payload.get("message", {}).get("toolCalls", [{}])[0]
    tool_call_id = tool_call.get("id")

    negotiation_result = tool_call.get("function", {}).get("arguments")
    recipient_phone = payload["message"]["customer"]["number"]

    events_collection.update_one(
        {
            "_id": ObjectId(negotiation_result["event_id"]),
            "venues.contact_phone_number": recipient_phone
        },
        {"$set": {
            "venues.$.negotiation_result": negotiation_result
        }}
    )

    result = {"status": "success", "message": "Negotiation result saved successfully"}
    return {"results": [{"toolCallId": tool_call_id, "result": result}]}


@app.post("/get_current_datetime")
async def get_current_datetime(request: Request):
    """Return the current datetime."""
    payload = await request.json()
    tool_call_id = payload.get("message", {}).get("toolCalls", [{}])[0].get("id")
    result = {"status": "success", "current_datetime": datetime.now(timezone.utc).strftime("%A, %B %d, %Y %I:%M %p")}
    return {"results": [{"toolCallId": tool_call_id, "result": result}]}


@app.get("/mongo_health")
def mongo_health_check():
    """Health check endpoint to verify MongoDB connection."""
    mongo_client.admin.command("ping")
    return {"status": "healthy", "database": "connected"}


@app.post("/vapi_health")
async def vapi_health_check(request: Request):
    """Health check endpoint to verify Vapi agent tool functionality."""
    payload = await request.json()
    tool_call_id = payload.get("message", {}).get("toolCalls", [{}])[0].get("id")
    result = {"status": "healthy", "message": "I don't like pineapple on pizza."}
    return {"results": [{"toolCallId": tool_call_id, "result": result}]}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
