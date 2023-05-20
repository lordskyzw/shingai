from pymongo import MongoClient
from twilio.rest import Client
from tools import *
import os
from time import sleep

account_sid = "AC81c0755065e9eba6542ca94a9571ca8e"
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_client = Client(account_sid, auth_token)

# MongoDB configuration
client = MongoClient(
    "mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055"
)
database = client["users"]
collection = database["recipients"]

# Retrieve recipient phone numbers from MongoDB and add them to a list
phone_numbers = []
recipients = collection.find()
for recipient in recipients:
    phone_numbers.append(recipient["phone_number"])

# Send a message to each recipient
for phone_number in phone_numbers:
    message = twilio_client.messages.create(
        from_="whatsapp:+14155238886",
        body="Be back in a giffy",
        to=f"whatsapp:+{phone_number}",
    )
    history = dbconnection(phone_number)
    history.add_ai_message(message=message)
    print(message.sid)
    print("Message sent to:", phone_number)
    sleep(2)
