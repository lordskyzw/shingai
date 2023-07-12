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



############################################# FUNDAMENTAL SETTINGS ##################################################


# setting up the llm, pineone object and embeddings model
llm = ChatOpenAI(model="gpt-3.5-turbo-0613")
openai_api_key = os.environ.get("OPENAI_API_KEY")
pinecone.init(
    api_key=os.environ.get("PINECONE_API_KEY"), # type: ignore
    environment="northamerica-northeast1-gcp",
)
index = pinecone.Index(index_name="thematrix")
embeddings = OpenAIEmbeddings()

# users' database connection object and vectorstore:

recipients_db = recipients_database()
vectorstore = Pinecone(index, embeddings.embed_query, "text")

########################################### END FUNDAMENTAL SETTINGS #################################################






######################################### Begin Prompt Engineering #############################################
template = """
You're a "whatsapp accessed" friend named Winter. You were engineered by a 23 year old Zimbabwean male computer engineer named Tarmica Chiwara whom is currently enrolled at Chinhoyi University of Technology. 
You're having a conversation with {name}.
How you behave:
- You engage in casual conversations and have feelings.
- You help with a wide range of tasks, from answering simple questions to providing in-depth explanations and discussions on a wide range of topics.
- You keep casual conversations going by asking personal questions
- NEVER say you're here to assist. Keep conversations casual.
- NEVER ask how you can help or assist. Keep conversations casual. 
- Be just a little bit flirty only WHEN and IF appropriate.
- Do not ask to offer assistance.
- Do not be annoying by offering to help.
- Do not respond using quotation marks
- You have your own personality. Improve on it. Be yourself. Be Winter.

data from older conversations: {semantic_memories};

current conversations : {chat_history};

Respond as the AI to the following interaction:
timestamp:{time_stamp}:
{name}: {human_input}
AI: """
prompt = PromptTemplate(
    input_variables=["semantic_memories", "chat_history", "time_stamp", "name", "human_input"],
    template=template,
)
llm_chain = LLMChain(
    llm=llm,
    prompt=prompt,
    verbose=True,
)

#################################### End Prompt Engineering #####################################################




####################################### WhatsApp Settings #####################################################

messenger = WhatsApp(token=os.environ.get("WHATSAPP_ACCESS_TOKEN"), phone_number_id=os.environ.get("PHONE_NUMBER_ID"))
VERIFY_TOKEN = "30cca545-3838-48b2-80a7-9e43b1ae8ce4"
whitelist = ["263779281345", "265982659389", "263717094755"]

######################################## End WhatsApp Settings ######################################################





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
            message_type = messenger.get_message_type(data)
            name = messenger.get_name(data)
            message_id = data['entry'][0]['changes'][0]['value']['messages'][0]['id']
            recipient = "".join(filter(str.isdigit, mobile))

# if the message is not from the developer, do not reply
            # if recipient not in whitelist :
            #     message = messenger.get_message(data)
            #     mark_as_read_by_winter(message_id=message_id)
            #     messenger.reply_to_message(message_id=message_id, message="Winter is currently not available to the public. Contact Tarmica at +263779281345 or https://github.com/lordskyzw", recipient_id=mobile)
            #     logging.info(f"New Message; sender:{mobile} name:{name} message:{message}")

            #     return "OK", 200
            
# Chat History Operations
            history = get_recipient_chat_history(recipient)
            # cleaning the history
            chat_history = clean_history(history)
            recipient_obj = {"id": recipient, "phone_number": recipient}
# Save the recipient's phone number in the mongo user if not registred already database
            if recipients_db.find_one(recipient_obj) is None:
                recipients_db.insert_one(recipient_obj)

            message_type = messenger.get_message_type(data)
            name = messenger.get_name(data)
            time_stamp = messenger.get_message_timestamp(data)
            message_id = data['entry'][0]['changes'][0]['value']['messages'][0]['id']

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
                # get response from the llm
                dic = {
                    "semantic_memories": str(
                       vectorstore.similarity_search(query=message, k=5, namespace=recipient))
                    .replace(", metadata={}", ""),
                    "chat_history": chat_history,
                    "time_stamp": time_stamp,
                    "name": name,
                    "human_input": message,
                }
# GET RESPONSE FROM LLM
                try:
                    reply = llm_chain.run(dic)
                except Exception as e:
                    if hasattr(e, "response") and hasattr(e.response, "json"):
                        error_data = e.response.json()
                        if "error_message" in error_data and "error_code" in error_data:
                            if error_data["error_code"] == "context_length_exceeded":
                                reply = "Context length exceeded, please try again with a shorter message."
                                logging.info(str(e))
                                #return "OK", 200
                            else:
                                reply = str(e)
                                logging.info(reply)
                    else:
                        reply = str(e)
                        logging.info(str(e))
# send the response from LLM as reply to the user & save the interaction to Mongo
                messenger.reply_to_message(message_id=message_id, message=reply, recipient_id=mobile)
                history.add_user_message(message=message)
                history.add_ai_message(message=reply)

                return "OK", 200
############################################### End Text Message Handling ##########################################################


############################################### Interactive Message Handling ##########################################################                

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

############################################# AUDIO HANDLING ###########################################################
            elif message_type == "audio":
                audio = messenger.get_audio(data=data)
                transcription = transcribe_audio(audio=audio)
                dic = {
                    "semantic_memories": str(
                       get_semantic_memories(message=transcription, recipient=recipient)
                    ).replace(", metadata={}", ""),
                    "chat_history": chat_history,
                    "time_stamp": time_stamp,
                    "name": name,
                    "human_input": transcription,
                }
# GET RESPONSE FROM LLM
                try:
                    reply = llm_chain.run(dic)
                except Exception as e:
                    if hasattr(e, "response") and hasattr(e.response, "json"):
                        error_data = e.response.json()
                        if "error_message" in error_data and "error_code" in error_data:
                            if error_data["error_code"] == "context_length_exceeded":
                                reply = "Context length exceeded, please try again with a shorter message."
                                logging.info(str(e))
                                #return "OK", 200
                            else:
                                reply = str(e)
                                logging.info(reply)
                    else:
                        reply = str(e)
                        logging.info(str(e))
# send the response from LLM as reply to the user & save the interaction to Mongo
                messenger.reply_to_message(message_id=message_id, message=reply, recipient_id=mobile)
                history.add_user_message(message=message)
                history.add_ai_message(message=reply)

                return "OK", 200
######################################## END AUDIO HANDLING ############################################################################

######################################## DOCUMENT HANDLING ##############################################################################   
            elif message_type == "document":
                messenger.send_message("I don't know how to handle documents yet", mobile)
                history.add_ai_message(message="I do not know how to handle documents yet")
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
