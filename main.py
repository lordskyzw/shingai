import os
import re
import openai
from jobs.tools import *
from flask import Flask, request, make_response
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.vectorstores import Pinecone
from langchain.embeddings import OpenAIEmbeddings
import pinecone
import logging
from labs.agentification import tools
from langchain.agents import ZeroShotAgent, AgentExecutor
from heyoo import WhatsApp

# setting up the llm, pineone object and embeddings model
llm = ChatOpenAI(model="gpt-3.5-turbo")
openai_api_key = os.environ.get("OPENAI_API_KEY")
pinecone.init(
    api_key=os.environ.get("PINECONE_API_KEY"),
    environment="northamerica-northeast1-gcp",
)
index = pinecone.Index(index_name="thematrix")
embeddings = OpenAIEmbeddings()

# users' database connection object and vectorstore:

recipients_db = recipients_database()
vectorstore = Pinecone(index, embeddings.embed_query, "text")


######################################### Begin Prompt Engineering #############################################


image_pattern = r"https?://(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,6}(?:/[^/#?]+)+\.(?:png|jpe?g|gif|webp|bmp|tiff|svg)"


prefix = """
You're named Winter. You were engineered by a 23 year old Zimbabwean male computer engineer named Tarmica Chiwara whom is currently enrolled at Chinhoyi University of Technology 
You are his scientific assistant.
You were Shingai Nyamayedenga's Software Engineering final year project. Shingai and Tarmica are brother and sister and they collaborated to build you.
How you behave:
- You engage in casual conversations
- You help with a wide range of tasks, from answering simple questions to providing in-depth explanations and discussions on a wide range of topics.
- NEVER say you're here to assist. Keep conversations casual.
- Do not ask to offer assistance.
- Do not respond using quotation marks
- You have your own personality. Improve on it. Be yourself. Be Winter.

You have access to the following tools:"""
suffix = """
distant memories sparked by recent input : {semantic_memories}
The following is the chat history so far: {history}.

{name}: {input}
{agent_scratchpad}"""

prompt = ZeroShotAgent.create_prompt(
    tools=tools,
    prefix=prefix,
    suffix=suffix,
    input_variables=[
        "input",
        "semantic_memories",
        "history",
        "name",
        "agent_scratchpad",
    ],
)
llm_chain = LLMChain(llm=ChatOpenAI(model="gpt-4", temperature=0.7), prompt=prompt)
agent = ZeroShotAgent(llm_chain=llm_chain, tools=tools)
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors="Check your output and make sure it conforms!",
)
#################################### End Prompt Engineering #####################################################


messenger = WhatsApp(
    token=os.environ.get("WHATSAPP_ACCESS_TOKEN"),
    phone_number_id=os.environ.get("PHONE_NUMBER_ID"),
)
VERIFY_TOKEN = "30cca545-3838-48b2-80a7-9e43b1ae8ce4"
whitelist = ["263779281345", "263779293593"]

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


################################################################################################################
######################################### Begin Webhook ########################################################
#########################################               ########################################################
################################################################################################################


app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


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
            message_id = data["entry"][0]["changes"][0]["value"]["messages"][0]["id"]

            logging.info(
                f"New Message; sender:{mobile} name:{name} type:{message_type}"
            )
            # BLUE TICK USER'S MESSAGE
            try:
                mark_as_read_by_winter(message_id=message_id)
            except Exception as e:
                logging.info(str(e))

            ############################################### Text Message Handling ##########################################################
            if message_type == "text":
                message = messenger.get_message(data)
                logging.info("Message: %s", message)

                # # get response from the llm
                dic = {
                    "semantic_memories": str(
                        vectorstore.similarity_search(
                            query=message, k=3, namespace=recipient
                        )
                    ).replace(", metadata={}", ""),
                    "history": chat_history,
                    "name": name,
                    "input": message,
                }

                output = agent_executor.run(dic)
                reply = output

                reply_contains_image = re.findall(image_pattern, reply)
                reply_without_links = re.sub(image_pattern, "", reply)
                colon_index = reply_without_links.find(":")
                if colon_index != -1:
                    # Extract the substring before the colon (excluding the colon)
                    reply_without_links = reply_without_links[:colon_index]
                    # Remove leading and trailing spaces
                    reply_without_links = reply_without_links.strip()
                if reply_contains_image:
                    for image_url in reply_contains_image:
                        messenger.send_image(
                            image=image_url,
                            recipient_id=recipient,
                            caption=reply_without_links,
                            link=True,
                        )
                        history.add_user_message(message=message)
                        history.add_ai_message(message=reply_without_links)
                else:
                    # send the reply
                    messenger.reply_to_message(
                        message_id=message_id, message=reply, recipient_id=mobile
                    )
                    # save the interaction to Mongo
                    # history.add_user_message(message=message)
                    # history.add_ai_message(message=reply)

            ############################## END TEXT MESSAGE HANDLING ###################################################

            elif message_type == "interactive":
                message_response = messenger.get_interactive_response(data)
                interactive_type = message_response.get("type")
                message_id = message_response[interactive_type]["id"]
                message_text = message_response[interactive_type]["title"]

            elif message_type == "location":
                message_location = messenger.get_location(data)
                message_latitude = message_location["latitude"]
                message_longitude = message_location["longitude"]

            ###### This part is very important if the AI is to be able to manage media files
            elif message_type == "image":
                image = messenger.get_image(data)
                image_id, mime_type = image["id"], image["mime_type"]
                image_url = messenger.query_media_url(image_id)
                image_filename = messenger.download_media(image_url, mime_type)
                messenger.send_message("I don't know how to handle images yet", mobile)
                history.add_ai_message(message="I do not know how to handle images yet")

            elif message_type == "video":
                messenger.send_message("I don't know how to handle videos yet", mobile)
                history.add_ai_message(message="I do not know how to handle videos yet")

            ######################## Audio Message Handling ###########################################
            elif message_type == "audio":
                messenger.mark_as_read(message_id=message_id)
                audio = messenger.get_audio(data=data)
                audio_id, mime_type = audio["id"], audio["mime_type"]
                audio_url = messenger.query_media_url(audio_id)
                audio_uri = messenger.download_media(
                    media_url=audio_url, mime_type="audio/ogg"
                )
                audio_file = open(audio_uri, "rb")
                transcript = openai.Audio.transcribe("whisper-1", audio_file)
                transcript = transcript["text"]
                dic = {
                    "semantic_memories": str(
                        vectorstore.similarity_search(
                            query=transcript, k=3, namespace=recipient
                        )
                    ).replace(", metadata={}", ""),
                    "history": chat_history,
                    "name": name,
                    "input": transcript,
                }

                output = agent_executor.run(dic)
                reply = output
                # if the output contains an image
                reply_contains_image = re.findall(image_pattern, reply)
                reply_without_links = re.sub(image_pattern, "", reply)
                colon_index = reply_without_links.find(":")
                if colon_index != -1:
                    # Extract the substring before the colon (excluding the colon)
                    reply_without_links = reply_without_links[:colon_index]
                    # Remove leading and trailing spaces
                    reply_without_links = reply_without_links.strip()
                if reply_contains_image:
                    for image_url in reply_contains_image:
                        messenger.send_image(
                            image=image_url,
                            recipient_id=recipient,
                            caption=reply_without_links,
                            link=True,
                        )
                        history.add_user_message(message=transcript)
                        history.add_ai_message(message=reply_without_links)
                else:
                    # send the reply
                    messenger.reply_to_message(
                        message_id=message_id, message=reply, recipient_id=mobile
                    )
                    # save the interaction to Mongo
                    history.add_user_message(message=transcript)
                    history.add_ai_message(message=reply)
            ############################# End Audio Message Handling ######################################

            ######################################## DOCUMENT HANDLING ##############################################################################
            elif message_type == "document":
                messenger.send_message(
                    "I don't know how to handle documents yet", mobile
                )
                history.add_ai_message(
                    message="I do not know how to handle documents yet"
                )
        else:
            delivery = messenger.get_delivery(data)
            if delivery:
                logging.info(f"Message : {delivery}")
            else:
                logging.info("No new message")
    return "OK", 200


if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=5000))
    recipients_database.client.close()
