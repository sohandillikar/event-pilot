import os
import json
import time
from dotenv import load_dotenv
from datetime import datetime, timezone

from pymongo import MongoClient
from bson.objectid import ObjectId
from vapi import Vapi

from typing import Optional

load_dotenv()

mongo_client = MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
mongo_client.admin.command("ping")
events_db = mongo_client["events_db"]
events_collection = events_db["events"]


class NegotiationAgent:
    def __init__(self, event_id: str):
        self.event_id = ObjectId(event_id)
        self.event = events_collection.find_one({"_id": self.event_id})
        if not self.event:
            raise ValueError(f"Event with ID {event_id} not found")
        
        self.venues = self.event.get("venues", [])
        self.vapi_client = Vapi(api_key=os.getenv("VAPI_API_KEY"))
        self.assistant_id = os.getenv("NEGOTIATION_ASSISTANT_ID")
        
        if not self.assistant_id:
            raise ValueError("NEGOTIATION_ASSISTANT_ID environment variable not set")
    
    def negotiate_with_venues(self):
        """Make outbound calls to all venues and conduct negotiations."""
        print(f"Starting negotiations for event {self.event_id}")
        print(f"Found {len(self.venues)} venues to contact")
        
        for i, venue in enumerate(self.venues):
            venue_name = venue.get("name", "Unknown")
            phone_number = venue.get("contact_phone_number")
            
            if not phone_number:
                print(f"Skipping venue {i+1}/{len(self.venues)} '{venue_name}': No phone number")
                continue
            
            print(f"\nCalling venue {i+1}/{len(self.venues)}: {venue_name} at {phone_number}")
            
            try:
                call_id = self._call_venue(venue)
                if call_id:
                    print(f"Call initiated successfully. Call ID: {call_id}")
                    # In a production system, you might want to wait for call completion
                    # or use webhooks to track call status
                else:
                    print(f"Failed to initiate call to {venue_name}")
            except Exception as e:
                print(f"Error calling {venue_name}: {str(e)}")
                # Update venue with error status
                self._update_venue_call_history(venue_name, None, "failed", str(e))
        
        print(f"\nCompleted negotiation calls for event {self.event_id}")
    
    def _call_venue(self, venue: dict) -> Optional[str]:
        """Make a single outbound call to a venue using Vapi SDK."""
        phone_number = venue.get("contact_phone_number")
        venue_name = venue.get("name", "Unknown Venue")
        
        if not phone_number:
            return None
        
        try:
            # Create outbound call with Vapi
            call = self.vapi_client.calls.create(
                phone_number_id=os.getenv("VAPI_PHONE_NUMBER_ID"),  # Your Vapi phone number
                customer={
                    "number": phone_number,
                    "name": venue_name
                },
                assistant_id=self.assistant_id,
                assistant_overrides={
                    "variableValues": {
                        "event_id": str(self.event_id),
                        "venue_name": venue_name
                    }
                }
            )
            
            # Record call in history
            call_id = call.id if hasattr(call, 'id') else str(call)
            self._update_venue_call_history(venue_name, call_id, "initiated", None)
            
            return call_id
            
        except Exception as e:
            print(f"Error creating Vapi call: {str(e)}")
            raise
    
    def _update_venue_call_history(self, venue_name: str, call_id: Optional[str], status: str, error: Optional[str]):
        """Update the call history for a specific venue."""
        try:
            call_record = {
                "call_id": call_id,
                "timestamp": datetime.now(timezone.utc),
                "status": status
            }
            
            if error:
                call_record["error"] = error
            
            # Update the specific venue in the venues array
            events_collection.update_one(
                {
                    "_id": self.event_id,
                    "venues.name": venue_name
                },
                {
                    "$push": {"venues.$.call_history": call_record}
                }
            )
        except Exception as e:
            print(f"Error updating call history: {str(e)}")
    
    def _wait_for_call_completion(self, call_id: str, timeout: int = 600) -> dict:
        """
        Poll for call completion status. 
        In production, you should use webhooks instead.
        
        Args:
            call_id: The Vapi call ID
            timeout: Maximum time to wait in seconds (default 10 minutes)
        
        Returns:
            Call status information
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                call = self.vapi_client.calls.get(call_id)
                status = call.status if hasattr(call, 'status') else None
                
                if status in ["ended", "completed", "failed", "no-answer", "busy"]:
                    return {
                        "call_id": call_id,
                        "status": status,
                        "duration": call.duration if hasattr(call, 'duration') else None
                    }
                
                # Wait before polling again
                time.sleep(5)
                
            except Exception as e:
                print(f"Error polling call status: {str(e)}")
                return {
                    "call_id": call_id,
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "call_id": call_id,
            "status": "timeout"
        }


def negotiate_venues_for_event(event_id: str):
    """
    Helper function to negotiate with all venues for a given event.
    Can be called from server.py or run standalone.
    """
    agent = NegotiationAgent(event_id)
    agent.negotiate_with_venues()


if __name__ == "__main__":
    # For testing purposes
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python negotiation_agent.py <event_id>")
        sys.exit(1)
    
    event_id = sys.argv[1]
    negotiate_venues_for_event(event_id)
