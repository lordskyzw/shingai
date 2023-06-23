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
        body="""📢 Attention, wonderful Winter users! 🤖🌟

We have an important announcement to share with you regarding Winter's availability. ❗️⚙️

Please be informed that Winter is currently undergoing further development and improvements. As a result, Winter's services may be unreliable even though she is available right now. ⏳🚧

We apologize for any inconvenience this may cause and appreciate your patience and understanding during this development phase. 🙏

That said, The Winter team is looking for a hobbyist python developer to learn from us and help alleviate the development workload. If you are interested, please contact Tarmica Chiwara at: +263 779 281 345. 📞👨‍💻


Once again, we apologize for any inconvenience caused and appreciate your ongoing support. We are excited to bring you an improved Winter very soon! 🌟😄



Thank you for your understanding and continued support!

Warm regards,
The Winter Team""",
        to=f"whatsapp:+{phone_number}",
    )
    history = get_recipient_chat_history(phone_number)
    history.add_ai_message(message=message.body) # type: ignore
    print(message.sid)
    print("Message sent to:", phone_number)
    sleep(1)
