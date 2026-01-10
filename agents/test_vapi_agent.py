import os
from dotenv import load_dotenv

from vapi import Vapi

load_dotenv()

client = Vapi(token=os.getenv("VAPI_API_KEY"))

ASSISTANT_ID = "5906decd-0226-4def-a88c-e20ad59a41cb"
PHONE_NUMBER_ID = "59974037-e0bd-4f56-9115-b22345365434"
CUSTOMER_NUMBER = "+14083388934"

call = client.calls.create(
    assistant_id=ASSISTANT_ID,
    phone_number_id=PHONE_NUMBER_ID,
    customer={"number": CUSTOMER_NUMBER},
)

print(f"Call created - {call.id}")