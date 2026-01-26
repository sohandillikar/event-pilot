import os
from dotenv import load_dotenv
import logging
import json

from vapi import Vapi, CreateFunctionToolDto
from supabase import create_client
import resend

from typing import Optional, Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

load_dotenv()

logger = logging.getLogger(__name__)
vapi_client = Vapi(token=os.getenv("VAPI_API_KEY"))
supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY"))
resend.api_key = os.getenv("RESEND_API_KEY")


def get_tool_ids():
    vapi_tools = vapi_client.tools.list()
    
    # Load tool schemas from tools.json
    tools_path = os.path.join(os.path.dirname(__file__), "tools.json")
    tool_schemas = json.load(open(tools_path))
    tool_ids = []
    
    # For each required tool, find or create it
    for tool_schema in tool_schemas:
        tool_name = tool_schema["function"]["name"]
        existing_tool = None

        for vapi_tool in vapi_tools:
            if vapi_tool.function.name == tool_name:
                existing_tool = vapi_tool
                break
        
        if existing_tool:
            tool_ids.append(existing_tool.id)
        else:
            new_tool = vapi_client.tools.create(request=CreateFunctionToolDto(**tool_schema))
            logger.info(f"[CREATED VAPI TOOL] - {tool_name} ({new_tool.id})")
            tool_ids.append(new_tool.id)
    
    return tool_ids


def create_vapi_agent(data: dict):
    logger.info(f"[FUNCTION CALL] - create_vapi_agent(data={data})")

    prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.md")
    with open(prompt_path, "r") as input_file:
        SYSTEM_PROMPT = input_file.read().replace("{{data}}", json.dumps(data))
    
    tool_ids = get_tool_ids()

    assistant_config_path = os.path.join(os.path.dirname(__file__), "assistant_config.json")
    assistant_config = json.load(open(assistant_config_path))
    assistant_config["model"]["messages"][0]["content"] = SYSTEM_PROMPT
    assistant_config["model"]["toolIds"] = tool_ids

    assistant = vapi_client.assistants.create(**assistant_config)
    return assistant


def start_negotiation(venue_id: str):
    logger.info(f"[FUNCTION CALL] - start_negotiation(venue_id={venue_id})")

    supabase_client.table("venues").update({
        "status": "negotiating"
    }).eq("id", venue_id).execute()
    venue = supabase_client.table("venues").select("*").eq("id", venue_id).execute().data[0]
    event = supabase_client.table("events").select("*").eq("id", venue.get("event_id")).execute().data[0]

    data = {
        "event": {
            "start_date": event.get("start_date"),
            "end_date": event.get("end_date"),
            "number_of_attendees": event.get("number_of_attendees"),
            "venue_type": event.get("venue_type"),
            "budget": event.get("budget_max")
        },
        "venue": {
            "id": venue.get("id"),
            "name": venue.get("name"),
            "website": venue.get("website"),
            "pricing_based_on_web_search": venue.get("pricing")
        }
    }

    agent = create_vapi_agent(data)
    call = vapi_client.calls.create(
        assistant_id=agent.id,
        phone_number_id=os.getenv("NEGOTIATION_PHONE_NUMBER_ID"),
        customer={"number": "+14083388934"}, # TODO: Change to venue.get("phone") for production
    )

    supabase_client.table("negotiations").insert({
        "event_id": event.get("id"),
        "venue_id": venue.get("id"),
        "vapi_call_id": call.id,
        "customer_budget_max": event.get("budget_max")
    }).execute()


class NegotiationResults(BaseModel):
    """Structured extraction of negotiation results from call transcript."""
    venue_initial_quote: Optional[int] = Field(None, description="The first price quote the venue provided (integer, no cents)")
    venue_initial_quote_breakdown: Optional[dict] = Field(None, description="Breakdown of initial quote as JSON object, e.g. {'room': 3000, 'catering': 2000, 'av': 500}")
    counteroffer: Optional[int] = Field(None, description="The counteroffer amount the event planner proposed (integer, no cents)")
    counteroffer_breakdown: Optional[dict] = Field(None, description="Breakdown of counteroffer as JSON object, e.g. {'room': 3000, 'catering': 2000, 'av': 500}")
    counteroffer_reasoning: Optional[str] = Field(None, description="Why the agent offered this amount (e.g. 'Within client budget', 'Met in the middle')")
    venue_final_quote: Optional[int] = Field(None, description="The final price the venue agreed to after negotiation (integer, no cents)")
    venue_final_quote_breakdown: Optional[dict] = Field(None, description="Breakdown of final quote as JSON object, e.g. {'room': 3000, 'catering': 2000, 'av': 500}")
    venue_contact_person: Optional[str] = Field(None, description="Name of the person at the venue who was on the call")
    venue_availability: Optional[Literal['available', 'tentatively_available', 'not_available']] = Field(None, description="Venue's availability status")
    venue_flexibility: Optional[Literal['flexible', 'semi_flexible', 'not_flexible']] = Field(None, description="How flexible the venue was during negotiation")
    restrictions: Optional[list] = Field(default_factory=list, description="List of any restrictions or limitations the venue mentioned (e.g. ['no outdoor events', 'must end by 10pm'])")
    notes: Optional[str] = Field(None, description="Any additional important notes or context from the conversation")


def save_negotiation_results(transcript: str, call_id: str):
    logger.info("[FUNCTION CALL] - save_negotiation_results(transcript=...)")

    # Convert transcript into readable format for LLM
    transcript = transcript.split("\n")
    for i, line in enumerate(transcript):
        if line.startswith("User:"):
            transcript[i] = line.replace("User:", "Venue:").strip()
        elif line.startswith("AI:"):
            transcript[i] = line.replace("AI:", "Event Planner:").strip()
    transcript = "\n".join(transcript)

    # Get event and venue data from public.negotiations table
    data = supabase_client.table("negotiations")\
        .select("events(*), venues(*)")\
        .eq("vapi_call_id", call_id)\
        .execute().data[0]

    event = data["events"]
    venue = data["venues"]

    data = {
        "event": {
            "start_date": event.get("start_date"),
            "end_date": event.get("end_date"),
            "number_of_attendees": event.get("number_of_attendees"),
            "venue_type": event.get("venue_type"),
            "budget": event.get("budget_max")
        },
        "venue": {
            "name": venue.get("name"),
            "pricing_based_on_web_search": venue.get("pricing")
        }
    }

    SYSTEM_PROMPT = f"""
    Extract negotiation details from this call transcript between an event planner and a venue.
    
    CONTEXT:
    The event planner was negotiating for an event with the following details:
    {json.dumps(data)}
    
    Only extract information that was explicitly mentioned in the conversation. If something wasn't discussed, leave it as null.
    """.strip()

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{transcript}")
    ])
    llm = ChatOpenAI(model="gpt-4o-mini").with_structured_output(NegotiationResults)
    chain = prompt | llm
    response = chain.invoke({"transcript": transcript})
    
    # Update the negotiations table
    update_data = {
        "venue_initial_quote": response.venue_initial_quote,
        "venue_initial_quote_breakdown": response.venue_initial_quote_breakdown,
        "agent_counteroffer": response.counteroffer,
        "agent_counteroffer_breakdown": response.counteroffer_breakdown,
        "agent_counteroffer_reasoning": response.counteroffer_reasoning,
        "venue_final_quote": response.venue_final_quote,
        "venue_final_quote_breakdown": response.venue_final_quote_breakdown,
        "venue_contact_person": response.venue_contact_person,
        "venue_availability": response.venue_availability,
        "venue_flexibility": response.venue_flexibility,
        "restrictions": response.restrictions,
        "notes": response.notes
    }
    
    # Remove None values to avoid overwriting with null
    update_data = {k: v for k, v in update_data.items() if v is not None}
    
    # Update the row where vapi_call_id matches
    supabase_client.table("negotiations")\
        .update(update_data)\
        .eq("vapi_call_id", call_id)\
        .execute()
    
    return response


def email_customer_about_negotiation(call_id: str):
    logger.info(f"[FUNCTION CALL] - email_customer_about_negotiation(call_id={call_id})")


if __name__ == "__main__":
    start_negotiation("")