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

openai_api_key = os.environ.get("OPENAI_API_KEY")
pinecone.init(
    api_key=os.environ.get("PINECONE_API_KEY"),
    environment="northamerica-northeast1-gcp",
)

index = pinecone.Index(index_name="thematrix")
embeddings = OpenAIEmbeddings()

# database for users:
client = MongoClient(
    "mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055"
)
database = client["users"]
collection = database["recipients"]


app = Flask(__name__)


@app.route("/chat", methods=["POST"])
def chat():
    recipient = request.form.get("From")
    # Strip special characters and formatting from the phone number
    recipient = "".join(filter(str.isdigit, recipient))

    # Save the recipient's phone number in the mongo user database
    recipient_obj = {"id": recipient, "phone_number": recipient}
    collection.insert_one(recipient_obj)

    # Get the message, make vector embeddings
    message = request.form.get("Body")
    vectorstore = Pinecone(index, embeddings.embed_query, "text", namespace=recipient)

    # Load up the specific user chat history from  the mongodb
    history = dbconnection(recipient)

    # add embeddings to the vector database
    # vectorstore.add_texts(history.messages, namespace=recipient)

    # begin Prompt Engineering
    template = """
    {chat_history}
    
    {context}
    
    You are an AI named Winter, posing as a human. You were created by a computer engineern (23 year old Zimbabwean male) named Tarmica Chiwara in 2023 enrolled at Chinhoyi University of Technology. 
    You are having a conversation with another human. Using the above as chat history and context, if there is none, proceed naturally.
    You are not a servant but a friend.
    Only when appropriate, ask the user questions for engagement to make them feel acquinted but do not be intrusive! Respond as the AI to the following interaction:
    Human: {human_input}
    AI: """
    prompt = PromptTemplate(
        input_variables=["chat_history", "context", "human_input"], template=template
    )
    llm_chain = LLMChain(
        llm=ChatOpenAI(
            model_name="gpt-3.5-turbo",
            openai_api_key=openai_api_key,
            temperature=0.7,
        ),
        prompt=prompt,
        verbose=True,
    )
    dic = {
        "context": str(
            vectorstore.similarity_search(query=message, namespace=recipient, k=3)
        ),
        "chat_history": str(history.messages[-5:]),
        "human_input": message,
    }

    # get response from the llm
    reply = llm_chain.run(dic)

    # save the interaction to Postgres and Vectorstore
    history.add_user_message(message=message)
    history.add_ai_message(message=reply)
    # vectorstore.add_texts(reply, namespace=recipient)

    # Send the reply back to the WhatsApp number
    response = MessagingResponse()
    response.message(reply)
    return str(response)


if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=5000))
    client.close()
