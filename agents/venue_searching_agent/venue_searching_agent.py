import os
import json
from dotenv import load_dotenv
from datetime import datetime

from pymongo import MongoClient
from bson.objectid import ObjectId
from tavily import TavilyClient
from openai import OpenAI
import googlemaps
import phonenumbers

from typing import Optional
from pydantic import BaseModel, Field

load_dotenv()

mongo_client = MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
mongo_client.admin.command("ping")
events_db = mongo_client["events_db"]
events_collection = events_db["events"]

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
gmaps_client = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

def two_letter_state_code(state_name: str) -> str:
    state_codes = json.load(open("state_codes.json"))
    state_codes = {v: k for k, v in state_codes.items()}
    try:
        return state_codes[state_name]
    except:
        return state_name

def get_gmaps_place_id(query):
    result = gmaps_client.places(query)
    if result['results']:
        return result['results'][0]['place_id']

def convert_phone_number_to_e164(phone_number, country_code='US'):
    parsed_number = phonenumbers.parse(phone_number, country_code)
    if phonenumbers.is_valid_number(parsed_number):
        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)

def get_phone_number(place_query):
    # TODO: Remove this for production
    return "+14083388934"
    place_id = get_gmaps_place_id(place_query)
    place = gmaps_client.place(place_id=place_id, fields=['international_phone_number', 'formatted_phone_number'])["result"]
    intl_phone = place.get('international_phone_number')
    if intl_phone:
        intl_phone = convert_phone_number_to_e164(intl_phone)
        if intl_phone:
            return intl_phone
    fmt_phone = place.get('formatted_phone_number')
    if fmt_phone:
        fmt_phone = convert_phone_number_to_e164(fmt_phone)
        if fmt_phone:
            return fmt_phone


class VenueDetails(BaseModel):
    name: str = Field(description="The name of the venue")
    capacity: Optional[int] = Field(default=None, description="Maximum number of guests the venue can accommodate")
    pricing_min: Optional[int] = Field(default=None, description="Minimum price in USD")
    pricing_max: Optional[int] = Field(default=None, description="Maximum price in USD")
    location: Optional[str] = Field(default=None, description="Address or neighborhood of the venue")
    amenities: Optional[list[str]] = Field(default=None, description="List of amenities the venue offers")
    url: Optional[str] = Field(default=None, description="URL to the venue's listing or website")

class ContactDetails(BaseModel):
    contact_email: Optional[str] = Field(default=None, description="Contact email of the venue")
    contact_phone_number: Optional[str] = Field(default=None, description="Contact phone number in E.164 format (e.g., +14083388934)")

class VenueSearchResponse(BaseModel):
    venues: list[VenueDetails] = Field(description="List of venues that best match the event requirements")

class VenueSearchingAgent:
    def __init__(self, event_id: str):
        self.event_id = ObjectId(event_id)
        self.event = events_collection.find_one({"_id": self.event_id})
        self.venues = self.event.get("venues", [])

    def _extract_best_venues(self, venue_type: str, city: str, state: str, attendees: int, days: int, budget: int, raw_content: str):
        SYSTEM_PROMPT = f"""
        You are a venue searching assistant. Given a list of venues in an unstructured format, only extract details for the venues that best fit the event requirements. If there are no venues that fit the event requirements, return an empty list.

        Event requirements:
        - Venue type: {venue_type}
        - Location: {city}, {state}
        - Number of attendees: {attendees}
        - Number of days: {days}
        - Budget: ${budget}
        """.strip()

        response = openai_client.responses.parse(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_content},
            ],
            text_format=VenueSearchResponse
        )

        return response.output_parsed

    def search_venues(self):
        """Use Tavily to search for venues that best match the event requirements."""
        best_venues = []

        venue_type = self.event.get("venue_type", "Corporate Event")
        state = two_letter_state_code(self.event["location_state"])
        city = self.event["location_city"]
        budget = self.event["budget"]
        attendees = self.event["number_of_attendees"]
        
        start_date = datetime.strptime(self.event["start_date"], "%Y-%m-%d")
        end_date = datetime.strptime(self.event["end_date"], "%Y-%m-%d")
        days = (end_date - start_date).days + 1

        if days > 1:
            days_str = f"{days} days"
        else:
            days_str = f"{days} day"

        query = f"{venue_type} venues in {city}, {state} for {attendees} guests and {days_str} under ${budget}"
        search_response = tavily_client.search(query)
        print(f"Finished Tavily search for '{query}'")
        urls = [result["url"] for result in search_response["results"]]

        if len(urls) > 0:
            extract_response = tavily_client.extract(urls)
            print(f"Finished Tavily extract for {len(urls)} urls")
            for i, result in enumerate(extract_response["results"]):
                venues = self._extract_best_venues(venue_type, city, state, attendees, days, budget, result["raw_content"])
                best_venues.extend(venues.model_dump()["venues"])
                print(f"Finished LLM extraction for {i+1}/{len(urls)} urls")

        return best_venues

    def extract_venue_contact_info(self, venues: list[dict] = None):
        if venues is None:
            venues = self.venues
        for i, venue in enumerate(venues):
            if venue.get("location"):
                query = f"{venue.get('name')}, {venue.get('location')}"
            else:
                query = venue.get("name")
            phone_number = get_phone_number(query)
            venues[i]["contact_phone_number"] = phone_number
        return venues

    def save_venues(self, venues: list[dict]):
        """Save the venues to MongoDB Atlas."""
        venues_to_save = [v for v in venues if v.get("url") and v.get("url").startswith("http")]
        events_collection.update_one(
            {"_id": self.event_id},
            {"$set": {"venues": venues_to_save}}
        )
        self.event = events_collection.find_one({"_id": self.event_id})
        self.venues = self.event["venues"]
        return self.venues