from pymongo import MongoClient
from heyoo import WhatsApp
from time import sleep
import os


messenger = WhatsApp(token=os.environ.get("WHATSAPP_ACCESS_TOKEN"), phone_number_id=os.environ.get("PHONE_NUMBER_ID"))

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
    messenger.send_message(message=
        """hey, it's Winter.

        This is the new permanent WhatsApp number now! 🥳
        
        This may be the last time you'll be receiving a broadcast message like this. 

        Thank you for enduring that whole joining phrase phase (that was a tongue twister!) 🙏🏾🤖🌟.


""", recipient_id=phone_number)
    
    print("Message sent to:", phone_number)
    sleep(1)
