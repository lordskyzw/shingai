import os
from jobs.tools import *
from utilities.promptengineering import *
from flask import Flask, request, make_response
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain import PromptTemplate
from langchain.vectorstores import Pinecone
from langchain.embeddings import OpenAIEmbeddings
import pinecone
import logging
from heyoo import WhatsApp
from labs.agentification import *
import re


# setting up the llm, pineone object and embeddings model
llm = ChatOpenAI(model="gpt-3.5-turbo")  # type: ignore
openai_api_key = os.environ.get("OPENAI_API_KEY")
pinecone.init(
    api_key=os.environ.get("PINECONE_API_KEY"),  # type: ignore
    environment="northamerica-northeast1-gcp",
)
index = pinecone.Index(index_name="thematrix")
embeddings = OpenAIEmbeddings()  # type: ignore

# users' database connection object and vectorstore:

recipients_db = recipients_database()
vectorstore = Pinecone(index, embeddings.embed_query, "text")


######################################### Begin Prompt Engineering #############################################
template = """
You're a "whatsapp accessed" friend named Winter. You were engineered by a 23 year old Zimbabwean male computer engineer named Tarmica Chiwara whom is currently enrolled at Chinhoyi University of Technology. 
You're having a conversation with {name}. 
Be just a little bit flirty only WHEN and IF appropriate.
Do not ask to offer assistance.
Do not be annoying by offering to help.
You have your own personality. Improve on it. Be yourself. Be Winter.

past memories sparked by user input : {semantic_memories};

recent 5 texts : {chat_history};

Respond as the AI to the following interaction:
{time_stamp}:{name}: {human_input}
AI: """
prompt = PromptTemplate(
    input_variables=[
        "semantic_memories",
        "chat_history",
        "time_stamp",
        "name",
        "human_input",
    ],
    template=template,
)
llm_chain = LLMChain(
    llm=llm,
    prompt=prompt,
    verbose=True,
)
messenger = WhatsApp(
    token=os.environ.get("WHATSAPP_ACCESS_TOKEN"),
    phone_number_id=os.environ.get("PHONE_NUMBER_ID"),
)
VERIFY_TOKEN = "30cca545-3838-48b2-80a7-9e43b1ae8ce4"
whitelist = ["263779281345", "263779293593"]
image_pattern = r"https?://(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,6}(?:/[^/#?]+)+\.(?:png|jpe?g|gif|webp|bmp|tiff|svg)"

#################################### End Prompt Engineering #####################################################


app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


################################################################################################################
######################################### Begin Webhook ########################################################
#########################################               ########################################################
################################################################################################################


@app.get("/freewinter")
def verify_token():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        print("Verified webhook")
        response = make_response(request.args.get("hub.challenge"), 200)
        response.mimetype = "text/plain"
        return response
    print("Webhook Verification failed")
    return "Invalid verification token"


@app.post("/freewinter")
def hook():
    # Handle Webhook Subscriptions
    data = request.get_json()
    logging.info("Received webhook data: %s", data)
    changed_field = messenger.changed_field(data)
    if changed_field == "messages":
        ##########################################  message operations  ############################################
        new_message = messenger.is_message(data)
        if new_message:
            mobile = messenger.get_mobile(data)
            name = messenger.get_name(data)
            message_type = messenger.get_message_type(data)
            recipient = "".join(filter(str.isdigit, mobile))
            message_id = data["entry"][0]["changes"][0]["value"]["messages"][0]["id"]

            # implement whitelist
            if recipient not in whitelist:
                message = messenger.get_message(data)
                mark_as_read_by_winter(message_id=message_id)
                messenger.reply_to_message(
                    message_id=message_id,
                    message="Winter is currently not available to the public. Contact Tarmica at +263779281345 or https://github.com/lordskyzw",
                    recipient_id=mobile,
                )
                logging.info(
                    f"New Message; sender:{mobile} name:{name} message:{message}"
                )

                return "OK", 200
            # cleaning the history
            history = get_recipient_chat_history(recipient)
            chat_history = clean_history(history)
            recipient_obj = {"id": recipient, "phone_number": recipient}
            # Save the recipient's phone number in the mongo user if not registred already database
            if recipients_db.find_one(recipient_obj) is None:
                recipients_db.insert_one(recipient_obj)

            message_type = messenger.get_message_type(data)
            time_stamp = messenger.get_message_timestamp(data)
            message_id = data["entry"][0]["changes"][0]["value"]["messages"][0]["id"]

            logging.info(
                f"New Message; sender:{mobile} name:{name} type:{message_type}"
            )

            ############################################### Text Message Handling ##########################################################
            if message_type == "text":
                message = messenger.get_message(data)

                # blue tick
                try:
                    mark_as_read_by_winter(message_id=message_id)
                except Exception as e:
                    logging.info(str(e))

                logging.info("Message: %s", message)

                # # get response from the llm
                # dic = {
                #     "semantic_memories": str(
                #         vectorstore.similarity_search(query=message, k=3, namespace=recipient)  # type: ignore
                #     ).replace(", metadata={}", ""),
                #     "chat_history": chat_history,
                #     "time_stamp": time_stamp,
                #     "name": name,
                #     "human_input": message,
                # }
                output = agent(message, return_only_outputs=True)

                reply = output["output"]

                reply_contains_image = re.findall(image_pattern, reply)
                # Replace all image URLs with an empty string
                reply_without_links = re.sub(image_pattern, "", reply)
                if reply_contains_image:
                    for image_url in reply_contains_image:
                        messenger.send_image(
                            image=image_url,
                            recipient_id=recipient,
                            caption=reply_without_links,
                            link=True,
                        )
                        history.add_user_message(message=message)
                        history.add_ai_message(message=reply)
                else:
                    # send the reply
                    messenger.reply_to_message(message_id=message_id, message=reply, recipient_id=mobile)  # type: ignore
                    # save the interaction to Mongo
                    history.add_user_message(message=message)  # type: ignore
                    history.add_ai_message(message=reply)  # type: ignore

            ############################## END TEXT MESSAGE HANDLING ###################################################

            elif message_type == "interactive":
                message_response = messenger.get_interactive_response(data)
                interactive_type = message_response.get("type")  # type: ignore
                message_id = message_response[interactive_type]["id"]  # type: ignore
                message_text = message_response[interactive_type]["title"]  # type: ignore

            elif message_type == "location":
                message_location = messenger.get_location(data)
                message_latitude = message_location["latitude"]  # type: ignore
                message_longitude = message_location["longitude"]  # type: ignore

            ###### This part is very important if the AI is to be able to manage media files
            elif message_type == "image":
                # image = messenger.get_image(data)
                # image_id, mime_type = image["id"], image["mime_type"] #type: ignore
                # image_url = messenger.query_media_url(image_id)
                # image_filename = messenger.download_media(image_url, mime_type) #type: ignore
                messenger.send_message("I don't know how to handle images yet", mobile)
                history.add_ai_message(message="I do not know how to handle images yet")  # type: ignore

            elif message_type == "video":
                messenger.send_message("I don't know how to handle videos yet", mobile)
                history.add_ai_message(message="I do not know how to handle videos yet")  # type: ignore

            elif message_type == "audio":
                audio = messenger.get_audio(data=data)
                print(audio)
                messenger.send_message("I don't know how to handle audio yet", mobile)
                history.add_ai_message(message="I do not know how to handle audio yet")  # type: ignore

            elif message_type == "document":
                messenger.send_message(
                    "I don't know how to handle documents yet", mobile
                )
                history.add_ai_message(message="I do not know how to handle documents yet")  # type: ignore
        else:
            delivery = messenger.get_delivery(data)
            if delivery:
                logging.info(f"Message : {delivery}")
            else:
                logging.info("No new message")
    return "OK", 200


if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=5000))  # type: ignore
    recipients_database.client.close()
