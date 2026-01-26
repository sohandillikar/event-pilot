import os
from dotenv import load_dotenv

from fastapi import APIRouter, Request
from supabase import create_client
from tavily import TavilyClient

load_dotenv()

router = APIRouter()
PREFIX = "/negotiation"

supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


@router.post(f"{PREFIX}/get_past_negotiations")
async def get_past_negotiations(request: Request):
    """Get past negotiations with a venue."""
    payload = await request.json()
    tool_call = payload.get("message", {}).get("toolCalls", [{}])[0]
    tool_call_id = tool_call.get("id")

    # Get parameters from tool call
    parameters = tool_call.get("function", {}).get("arguments", {})

    venue_id = parameters.get("venue_id")
    
    # Step 1: Get google_place_id for the input venue
    venue_response = supabase_client.table("venues").select("google_place_id").eq("id", venue_id).execute()
    
    if not venue_response.data or len(venue_response.data) == 0:
        return {"results": [{"toolCallId": tool_call_id, "result": {"error": "Venue not found"}}]}
    
    google_place_id = venue_response.data[0]["google_place_id"]
    
    # Step 2: Get all venue_ids with the same google_place_id
    venue_ids_response = supabase_client.table("venues").select("id").eq("google_place_id", google_place_id).execute()
    matching_venue_ids = [v["id"] for v in venue_ids_response.data]
    
    # Step 3: Get all negotiations for these venues (only where venue_final_quote is not null)
    negotiations_response = supabase_client.table("negotiations")\
        .select("created_at, event_id, venue_initial_quote, venue_initial_quote_breakdown, customer_budget_max, agent_counteroffer, agent_counteroffer_breakdown, agent_counteroffer_reasoning, venue_final_quote, venue_final_quote_breakdown")\
        .in_("venue_id", matching_venue_ids)\
        .not_.is_("venue_final_quote", "null")\
        .execute()
    
    # Step 4: Enrich with event details (number_of_attendees)
    result = []
    for negotiation in negotiations_response.data:
        event_response = supabase_client.table("events").select("number_of_attendees").eq("id", negotiation["event_id"]).execute()
        
        if event_response.data and len(event_response.data) > 0:
            result.append({
                "datetime": negotiation["created_at"],
                "number_of_attendees": event_response.data[0]["number_of_attendees"],
                "venue_initial_quote": negotiation["venue_initial_quote"],
                "venue_initial_quote_breakdown": negotiation["venue_initial_quote_breakdown"],
                "customer_budget": negotiation["customer_budget_max"],
                "counteroffer": negotiation["agent_counteroffer"],
                "counteroffer_breakdown": negotiation["agent_counteroffer_breakdown"],
                "counteroffer_reasoning": negotiation["agent_counteroffer_reasoning"],
                "venue_final_quote": negotiation["venue_final_quote"],
                "venue_final_quote_breakdown": negotiation["venue_final_quote_breakdown"]
            })
    
    return {"results": [{"toolCallId": tool_call_id, "result": {"past_negotiations": result}}]}


@router.post(f"{PREFIX}/web_search")
async def web_search(request: Request):
    """Search the web for information."""
    payload = await request.json()
    tool_call = payload.get("message", {}).get("toolCalls", [{}])[0]
    tool_call_id = tool_call.get("id")

    # Get parameters from tool call
    parameters = tool_call.get("function", {}).get("arguments", {})
    query = parameters.get("query")
    
    response = tavily_client.search(query=query, include_answer="basic")
    answer = response.get("answer")
    return {"results": [{"toolCallId": tool_call_id, "result": {"answer": answer}}]}


@router.post(f"{PREFIX}/webhook")
async def webhook(request: Request):
    """Handle webhook requests from VAPI."""
    payload = await request.json()
    message_type = payload.get("message", {}).get("type")

    if message_type == "end-of-call-report":
        print(payload)
    
    return {"status": "success"}