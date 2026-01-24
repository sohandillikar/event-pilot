import os
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from datetime import datetime, timezone
from supabase import create_client

load_dotenv()

router = APIRouter()
PREFIX = "/event_details"

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY"))


@router.post(f"{PREFIX}/get_current_datetime")
async def get_current_datetime(request: Request):
    """Return the current date, time and day of the week."""
    payload = await request.json()
    tool_call_id = payload.get("message", {}).get("toolCalls", [{}])[0].get("id")
    now = datetime.now(timezone.utc)
    result = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "day_of_week": now.strftime("%A")
    }
    return {"results": [{"toolCallId": tool_call_id, "result": result}]}


@router.post(f"{PREFIX}/get_user_information")
async def get_user_information(request: Request):
    """Return the user's information from public.users based on the phone number."""
    payload = await request.json()
    tool_call = payload.get("message", {}).get("toolCalls", [{}])[0]
    tool_call_id = tool_call.get("id")
    phone_number = payload["message"]["customer"]["number"]
    
    response = supabase.table("users").select("*").eq("phone", phone_number).execute()
    if response.data and len(response.data) > 0:
        user = response.data[0]
        result = {
            "user_id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "phone": user["phone"],
            "company": user["company"]
        }
    else:
        result = {"error": "User does not exist in the system"}
    return {"results": [{"toolCallId": tool_call_id, "result": result}]}


@router.post(f"{PREFIX}/save_user_information")
async def save_user_information(request: Request):
    """Save a new user to the database and return their user ID."""
    payload = await request.json()
    tool_call = payload.get("message", {}).get("toolCalls", [{}])[0]
    tool_call_id = tool_call.get("id")
    
    # Get parameters from tool call
    parameters = tool_call.get("function", {}).get("arguments", {})
    name = parameters.get("name")
    email = parameters.get("email")
    company = parameters.get("company")
    phone_number = payload["message"]["customer"]["number"]
    
    # Insert new user into Supabase
    response = supabase.table("users").insert({
        "name": name,
        "email": email,
        "phone": phone_number,
        "company": company
    }).execute()
    
    # Return the created user's ID
    if response.data and len(response.data) > 0:
        user = response.data[0]
        result = {"user_id": user["id"]}
    else:
        result = {"error": "Failed to save new user information to the database"}
    return {"results": [{"toolCallId": tool_call_id, "result": result}]}


@router.post(f"{PREFIX}/save_event_details")
async def save_event_details(request: Request):
    """Save event details to the database and return the event ID."""
    payload = await request.json()
    tool_call = payload.get("message", {}).get("toolCalls", [{}])[0]
    tool_call_id = tool_call.get("id")
    
    # Get parameters from tool call
    parameters = tool_call.get("function", {}).get("arguments", {})
    
    # Get phone number and look up user_id
    phone_number = payload["message"]["customer"]["number"]
    user_response = supabase.table("users").select("id").eq("phone", phone_number).execute()
    
    if not user_response.data or len(user_response.data) == 0:
        return {"results": [{"toolCallId": tool_call_id, "result": {"error": "User not found. Please register the user first."}}]}
    
    user_id = user_response.data[0]["id"]
    
    # Insert event into database
    event_data = {
        "user_id": user_id,
        "start_date": parameters.get("start_date"),
        "end_date": parameters.get("end_date"),
        "number_of_attendees": parameters.get("number_of_attendees"),
        "venue_type": parameters.get("venue_type"),
        "location_city": parameters.get("location_city"),
        "location_state": parameters.get("location_state"),
        "budget_min": parameters.get("budget_min"),
        "budget_max": parameters.get("budget_max")
    }
    
    # Add optional fields only if provided
    if parameters.get("required_amenities") is not None:
        event_data["required_amenities"] = parameters.get("required_amenities")
    if parameters.get("additional_details") is not None:
        event_data["additional_details"] = parameters.get("additional_details")
    
    response = supabase.table("events").insert(event_data).execute()
    
    # Return the created event's ID
    if response.data and len(response.data) > 0:
        event = response.data[0]
        result = {"event_id": event["id"]}
    else:
        result = {"error": "Failed to save event details"}
    return {"results": [{"toolCallId": tool_call_id, "result": result}]}