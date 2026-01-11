import os
from dotenv import load_dotenv

from vapi import Vapi

load_dotenv()

client = Vapi(token=os.getenv("VAPI_API_KEY"))

ASSISTANT_ID = "b962ebbe-5599-4b66-a236-01a7ad27b136"
PHONE_NUMBER_ID = "67b07df0-e27f-4201-98aa-b57a1f0a5aad"
CUSTOMER_NUMBER = "+14083388934"

call = client.calls.create(
    assistant_id=ASSISTANT_ID,
    phone_number_id=PHONE_NUMBER_ID,
    customer={"number": CUSTOMER_NUMBER},
)

print(f"Call created - {call.id}")