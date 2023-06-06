import os
from tools import *
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain import PromptTemplate
from langchain.vectorstores import Pinecone
from langchain.embeddings import OpenAIEmbeddings
import pinecone
from pymongo import MongoClient

# setting up the llm, pineone object and embeddings model
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    temperature=0.7,
    openai_api_key=os.environ.get("OPENAI_API_KEY"),
)
openai_api_key = os.environ.get("OPENAI_API_KEY")
pinecone.init(
    api_key=os.environ.get("PINECONE_API_KEY"),
    environment="northamerica-northeast1-gcp",
)
index = pinecone.Index(index_name="thematrix")
embeddings = OpenAIEmbeddings()

# users' database connection object and vectorstore:
client = MongoClient(
    "mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055"
)
database = client["users"]
collection = database["recipients"]
vectorstore = Pinecone(index, embeddings.embed_query, "text")

# begin Prompt Engineering
template = """
You're a "whatsapp accessed" AI named Winter.
You were created by a 23 year old Zimbabwean male computer engineer named Tarmica Chiwara in 2023 whom is currently enrolled at Chinhoyi University of Technology. 
You're having a conversation with a human. Use information below to respond. If you don't know the answer, please admit!

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
    recipient = request.form.get("From")
    # Strip special characters and formatting from the phone number
    recipient = "".join(filter(str.isdigit, recipient))
    # Save the recipient's phone number in the mongo user database
    recipient_obj = {"id": recipient, "phone_number": recipient}
    collection.insert_one(recipient_obj)

    message = request.form.get("Body")
    history = dbconnection(recipient)

    chat_history = str(history.messages[-5:]).replace(
        ", additional_kwargs={}, example=False", ""
    )
    chat_history.replace("content=", "")

    # get response from the llm
    dic = {
        "semantic_memories": str(
            vectorstore.similarity_search(query=message, k=1, namespace=recipient)
        ).replace(", metadata={}", ""),
        "chat_history": chat_history,
        "human_input": message,
    }
    reply = llm_chain.run(dic)

    # save the interaction to Mongo
    history.add_user_message(message=message)
    history.add_ai_message(message=reply)

    # Send the reply back to the WhatsApp number
    response = MessagingResponse()
    response.message(reply)
    return str(response)


if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=5000))
    client.close()
