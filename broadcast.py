from pymongo import MongoClient
from twilio.rest import Client
from tools import *
import os
from time import sleep

account_sid = os.environ.get("TWILIO_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_client = Client(account_sid, auth_token)

# MongoDB configuration
client = MongoClient(
    "mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055"
)
database = client["users"]
collection = database["recipients"]

# Retrieve recipient phone numbers from MongoDB and add them to a list
phone_numbers = set()
recipients = collection.find()
for recipient in recipients:
    phone_number = recipient["phone_number"]
    phone_numbers.add(phone_number)


# Convert the set back to a list if needed
phone_numbers = list(phone_numbers)

# Send a message to each recipient
for phone_number in phone_numbers:
    message = twilio_client.messages.create(
        from_="whatsapp:+14155238886",
        body="Apologies for the changes. ",
        to=f"whatsapp:+{phone_number}",
    )
    history = dbconnection(phone_number)
    history.add_ai_message(message=message.body)
    print(message.sid)
    print("Message sent to:", phone_number)
    sleep(2)
