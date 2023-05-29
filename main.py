import os
from tools import *
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

# from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain import PromptTemplate
from langchain.vectorstores import Pinecone
from langchain.embeddings import OpenAIEmbeddings
import pinecone
from langchain.llms import OpenAI
from pymongo import MongoClient

llm = OpenAI(
    model_name="text-davinci-003",
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
    vectorstore = Pinecone(index, embeddings.embed_query, "text")

    # Load up the specific user chat history from  the mongodb
    history = dbconnection(recipient)

    # add embeddings to the vector database
    # vectorstore.add_texts(history.messages, namespace=recipient)

    # begin Prompt Engineering
    template = """    
    {semantic_memories}
    
    {chat_history}
    
    You're an AI named Winter, posing as a human. You were created by a computer engineer (23 year old Zimbabwean male) named Tarmica Chiwara in 2023 who is currently enrolled at Chinhoyi University of Technology. 
    You're having a conversation with another human. Use the above as semantic memories & recent chat history, if there is none, proceed naturally.

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

    chat_history = str(history.messages[-5:]).replace(
        ", additional_kwargs={}, example=False", ""
    )
    chat_history.replace("content=", "")

    dic = {
        "semantic_memories": str(
            vectorstore.similarity_search(query=message, k=1, namespace=recipient)
        ).replace(", metadata={}", ""),
        "chat_history": chat_history,
        "human_input": message,
    }

    # get response from the llm
    reply = llm_chain.run(dic)

    # save the interaction to Mongo and Vectorstore
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
