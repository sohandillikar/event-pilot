import os
from dotenv import load_dotenv
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

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
