import os
import json
from dotenv import load_dotenv
from vapi import Vapi

load_dotenv()

def create_negotiation_assistant():
    """Create a Vapi assistant for venue negotiations."""
    
    # Initialize Vapi client
    vapi_client = Vapi(api_key=os.getenv("VAPI_API_KEY"))
    
    # Load system prompt
    with open("system_prompt.md", "r") as f:
        system_prompt = f.read()
    
    # Load assistant config
    with open("assistant_config.json", "r") as f:
        config = json.load(f)
    
    # Load tools
    with open("tools.json", "r") as f:
        tools = json.load(f)
    
    # Replace ${SYSTEM_PROMPT} placeholder
    config["model"]["messages"][0]["content"] = system_prompt
    
    # Add tools to config
    config["model"]["tools"] = tools
    
    try:
        # Create the assistant using Vapi SDK
        assistant = vapi_client.assistants.create(**config)
        
        print(f"✅ Successfully created negotiation assistant!")
        print(f"Assistant ID: {assistant.id}")
        print(f"Assistant Name: {assistant.name}")
        print(f"\n⚠️  IMPORTANT: Add this to your .env file:")
        print(f"NEGOTIATION_ASSISTANT_ID={assistant.id}")
        
        return assistant
        
    except Exception as e:
        print(f"❌ Error creating assistant: {str(e)}")
        raise


if __name__ == "__main__":
    create_negotiation_assistant()
