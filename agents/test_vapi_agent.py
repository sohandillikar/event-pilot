import os
from dotenv import load_dotenv

from vapi import Vapi

load_dotenv()

client = Vapi(token=os.getenv("VAPI_API_KEY"))

ASSISTANT_ID = "" # TODO: Replace with the actual assistant id
PHONE_NUMBER_ID = "" # TODO: Replace with the actual phone number id
CUSTOMER_NUMBER = "" # TODO: Replace with the actual customer number

call = client.calls.create(
    assistant_id=ASSISTANT_ID,
    phone_number_id=PHONE_NUMBER_ID,
    customer={"number": CUSTOMER_NUMBER},
)

print(f"Call created - {call.id}")