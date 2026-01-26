import os
from dotenv import load_dotenv

import logging
import googlemaps
import phonenumbers
from tavily import TavilyClient

from pydantic import BaseModel, Field
from langchain.agents import AgentState
from langchain.agents.middleware import before_model
from langchain_core.messages.utils import trim_messages
from langgraph.runtime import Runtime
from langchain.tools import tool

load_dotenv()

logger = logging.getLogger(__name__)

gmaps_client = googlemaps.Client(key=os.getenv("GOOGLE_PLACES_API_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def convert_phone_number_to_e164(phone_number: str, country_code: str = "US") -> str:
    parsed_number = phonenumbers.parse(phone_number, country_code)
    if phonenumbers.is_valid_number(parsed_number):
        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)


@before_model
def trim_messages_middleware(state: AgentState, runtime: Runtime):
    trimmed_messages = trim_messages(
        state["messages"],
        token_counter="approximate",
        max_tokens=4096,
        start_on="human",
        end_on=["human", "tool"]
    )
    state["messages"] = trimmed_messages
    return state


class SearchNearbyVenuesInput(BaseModel):
    city: str = Field(..., description="The city to search for venues in")
    state: str = Field(..., description="The 2-letter state code to search for venues in (e.g. CA, NY, etc.)", pattern="^[A-Z]{2}$")
    venue_type: str = Field(..., description="The type of venue to search for", enum=["hotel", "resort", "restaurant", "bar", "nightclub", "event space"])
    radius: int = Field(10000, description="The radius in meters to search for venues")
    max_results: int = Field(10, description="The maximum number of venues to return")


@tool(
    "search_nearby_venues",
    description="Search for venues near a given location",
    args_schema=SearchNearbyVenuesInput
)
def search_nearby_venues(
    city: str,
    state: str,
    venue_type: str,
    radius: int = 10000,
    max_results: int = 10
) -> list[dict]:
    logger.info(f"[TOOL CALL] - search_nearby_venues(city={city}, state={state}, venue_type={venue_type}, radius={radius}, max_results={max_results})")

    geocoded_location = gmaps_client.geocode(f"{city}, {state}")
    coordinates = geocoded_location[0]["geometry"]["location"]
    
    venue_type_mapping = {
        "hotel": "lodging",
        "resort": "lodging",
        "restaurant": "restaurant",
        "bar": "bar",
        "nightclub": "night_club",
        "event space": "event_venue"
    }
    
    places_nearby_result = gmaps_client.places_nearby(
        location=(coordinates["lat"], coordinates["lng"]),
        radius=radius,
        type=venue_type_mapping.get(venue_type.lower(), venue_type.lower())
    ).get("results", [])
    
    venues = []
    venue_ids = []
    
    for place in places_nearby_result:
        if place.get("business_status") != "OPERATIONAL":
            continue
        if len(venues) >= max_results:
            break
        place_id = place["place_id"]
        if place_id in venue_ids:
            continue

        place_details = gmaps_client.place(
            place_id=place_id,
            fields=["name", "formatted_address", "formatted_phone_number",
                   "website", "rating", "user_ratings_total", "type", "geometry"]
        ).get("result", {})

        phone_number = place_details.get("formatted_phone_number", place.get("international_phone_number"))
        if not phone_number:
            continue
        else:
            phone_number = convert_phone_number_to_e164(phone_number)

        website = place_details.get("website")
        if not website:
            continue
        else:
            website = website.split("?")[0]

        venues.append({
            "place_id": place_id,
            "name": place_details.get("name", place.get("name")),
            "address": place_details.get("formatted_address", place.get("vicinity")),
            "phone": phone_number,
            "website": website,
            "rating": place_details.get("rating"),
            "rating_count": place_details.get("user_ratings_total", 0),
            "location": {
                "lat": place_details.get("geometry", {}).get("location", {}).get("lat"),
                "lng": place_details.get("geometry", {}).get("location", {}).get("lng")
            },
            "types": place_details.get("types")
        })
        venue_ids.append(place_id)
    
    return venues


class GetVenuePricingInput(BaseModel):
    name: str = Field(..., description="The name of the venue")
    city: str = Field(..., description="The city of the venue")
    state: str = Field(..., description="The 2-letter state code of the venue (e.g. CA, NY, etc.)", pattern="^[A-Z]{2}$")


@tool(
    "get_venue_pricing",
    description="Get the total quote per person per night for any venue",
    args_schema=GetVenuePricingInput
)
def get_venue_pricing(name: str, city: str, state: str) -> str:
    logger.info(f"[TOOL CALL] - get_venue_pricing(name={name}, city={city}, state={state})")

    query = f"Total quote per person per night at {name} in {city}, {state}"
    response = tavily_client.search(query=query, include_answer="basic")
    answer = response.get("answer")
    return answer


class NegotiateWithVenueInput(BaseModel):
    venue_id: str = Field(..., description="The ID of the venue to negotiate with")


@tool(
    "negotiate_with_venue",
    description="Negotiate with a venue to get the best deal possible",
    args_schema=NegotiateWithVenueInput
)
def negotiate_with_venue(venue_id: str) -> str:
    logger.info(f"[TOOL CALL] - negotiate_with_venue(venue_id={venue_id})")
    # Change venue status to "negotiated" in Supabase
    return "Negotiation has begun"


class WebSearchInput(BaseModel):
    query: str = Field(..., description="The query to search the web for")


@tool(
    "web_search",
    description="Search the web for information",
    args_schema=WebSearchInput
)
def web_search(query: str) -> str:
    logger.info(f"[TOOL CALL] - web_search(query={query})")

    response = tavily_client.search(query=query, include_answer="basic")
    answer = response.get("answer")
    return answer