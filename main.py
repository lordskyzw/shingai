import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain import PromptTemplate
from langchain.memory import MongoDBChatMessageHistory

openai_api_key = os.environ.get("OPENAI_API_KEY")


app = Flask(__name__)


@app.route("/chat", methods=["POST"])
def chat():
    recipient = request.form.get("From")
    # Strip special characters and formatting from the phone number
    recipient = "".join(filter(str.isdigit, recipient))
    message = request.form.get("Body")

    # Load up the specific user chat history
    try:
        history = MongoDBChatMessageHistory(
            connection_string="mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055",
            database_name="test",
            session_id=recipient,
        )

    except Exception as e:
        return str(e)
    template = """
    {chat_history}
    
    using the above as context (chat history between human and chatbot), respond as a witty and human-like Chatbot to following interaction->
    Human: {human_input}
    Chatbot:"""
    prompt = PromptTemplate(
        input_variables=["chat_history", "human_input"], template=template
    )
    llm_chain = LLMChain(
        llm=OpenAI(
            model_name="text-davinci-003",
            openai_api_key=openai_api_key,
            temperature=0.7,
        ),
        prompt=prompt,
        verbose=True,
    )
    dic = {
        "human_input": message,
        "chat_history": str(history.messages[range(-1, -4[1])]),
    }
    reply = llm_chain.run(dic)

    # save the interaction to Postgres
    history.add_user_message(message=message)
    history.add_ai_message(reply)

    # Send the reply back to the WhatsApp number
    response = MessagingResponse()
    response.message(reply)
    return str(response)


if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=5000))
