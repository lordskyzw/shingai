import os
from jobs.tools import *
from utilities.promptengineering import *
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain import PromptTemplate
from langchain.vectorstores import Pinecone
from langchain.embeddings import OpenAIEmbeddings
import pinecone


account_sid = os.environ.get("TWILIO_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_client = Client(account_sid, auth_token)
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

# begin Prompt Engineering
template = """
You're a "whatsapp accessed" friend named Winter. You were created by a 23 year old Zimbabwean male computer engineer named Tarmica Chiwara in 2023 whom is currently enrolled at Chinhoyi University of Technology. 
You're having a conversation with a human. Make them feel warm and be a bit flirty. Do not ask to assist.

past memories sparked by user input : {semantic_memories};

recent 5 texts : {chat_history};

Respond as the AI to the following interaction:
Human: {human_input}
AI: """
prompt = PromptTemplate(
    input_variables=["semantic_memories", "chat_history", "human_input"],
    template=template,
)
llm_chain = LLMChain(
    llm=llm,
    prompt=prompt,
    verbose=True,
)


app = Flask(__name__)


@app.route("/chat", methods=["POST"])
def chat():
    ##########################################  phone number operations  ############################################

    recipient = request.form.get("From")
    # Strip special characters and formatting from the phone number
    recipient = "".join(filter(str.isdigit, recipient))
    recipient_obj = {"id": recipient, "phone_number": recipient}

    # Save the recipient's phone number in the mongo user if not registred already database
    if recipients_db.find_one(recipient_obj) is None:
        recipients_db.insert_one(recipient_obj)

    history = get_recipient_chat_history(recipient)
    # cleaning the history
    chat_history = clean_history(history)

    ##########################################  message operations  ############################################

    message = request.form.get("Body")
    # get response from the llm
    dic = {
        "semantic_memories": str(
            vectorstore.similarity_search(query=message, k=3, namespace=recipient)
        ).replace(", metadata={}", ""),
        "chat_history": chat_history,
        "human_input": message,
    }
    reply = llm_chain.run(dic)

    # save the interaction to Mongo
    history.add_user_message(message=message)
    history.add_ai_message(message=reply)

    # Send the reply back to the WhatsApp number
    twilio_client.messages.create(
        from_="whatsapp:+14155238886",
        body=reply,
        to=f"whatsapp:+{recipient}",
    )
    response = MessagingResponse()
    response.message(reply)
    return str(response)


# @app.route("/random_message", methods=["POST"])
# def random_message():
#     # Get a random recipient from the database
#     recipient = recipients_db.aggregate([{ "$sample": { "size": 1 } }]).next()["id"]
#     history = get_recipient_chat_history(recipient)
#     random_ai_message = create_random_message(clean_history=clean_history(history=history))

# ################################## Send the message to the recipient  #################################
#     try:
#         Client(os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN")).messages.create(to=recipient, from_="whatsapp:+14155238886", body=random_ai_message)
#         history.history.add_ai_message(message=random_ai_message)
#     except Exception as e:
#         print(str(e))
#         return str(e)

#     return str(random_ai_message)


if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=5000))
    recipients_database.client.close()
