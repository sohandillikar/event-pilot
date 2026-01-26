import os
from dotenv import load_dotenv
import json

from vapi import Vapi, CreateFunctionToolDto
from supabase import create_client

load_dotenv()

vapi_client = Vapi(token=os.getenv("VAPI_API_KEY"))
supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SECRET_KEY"))


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
            tool_ids.append(new_tool.id)
    
    return tool_ids


def create_vapi_agent(data: dict):
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


if __name__ == "__main__":
    tools = vapi_client.tools.list()
    for tool in tools:
        print(tool.function.name)
        exit()