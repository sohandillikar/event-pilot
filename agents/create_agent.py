import os
import json
from dotenv import load_dotenv

from vapi import Vapi, CreateFunctionToolDto

load_dotenv()

AGENT_DIRECTORY = "event_details_agent"

client = Vapi(token=os.getenv("VAPI_API_KEY"))

# Create the tools
tool_schemas = json.load(open(f"{AGENT_DIRECTORY}/tools.json"))
tool_ids = []

for schema in tool_schemas:
    tool = client.tools.create(request=CreateFunctionToolDto(**schema))
    tool_ids.append(tool.id)
    print(f"Created tool - {tool.id}")

# Create the agent
system_prompt = open(f"{AGENT_DIRECTORY}/system_prompt.md").read().strip()
assistant_config = json.load(open(f"{AGENT_DIRECTORY}/assistant_config.json"))
assistant_config["model"]["messages"][0]["content"] = system_prompt
assistant_config["model"]["toolIds"] = tool_ids

assistant = client.assistants.create(**assistant_config)
print(f"\nCreated assistant - {assistant.id}")