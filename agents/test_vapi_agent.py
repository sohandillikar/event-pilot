import os
from dotenv import load_dotenv

from vapi import Vapi

load_dotenv()

client = Vapi(token=os.getenv("VAPI_API_KEY"))

ASSISTANT_ID = "79f254d0-c534-45de-9f0f-8085a8bc4b2d"
PHONE_NUMBER_ID = "59974037-e0bd-4f56-9115-b22345365434"
CUSTOMER_NUMBER = "+14083388934"

call = client.calls.create(
    assistant_id=ASSISTANT_ID,
    phone_number_id=PHONE_NUMBER_ID,
    customer={"number": CUSTOMER_NUMBER},
)

print(f"Call created - {call.id}")