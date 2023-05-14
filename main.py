import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain import PromptTemplate
from langchain.memory.chat_message_histories import PostgresChatMessageHistory

openai_api_key = os.environ.get("OPENAI_API_KEY")

template = """You are having a conversation with a chatbot.

{chat_history}
Human: {human_input}
Chatbot:"""
prompt = PromptTemplate(
    input_variables=["chat_history", "human_input"], template=template
)
memory = ConversationBufferMemory(memory_key="chat_history")
llm_chain = LLMChain(
    llm=OpenAI(
        model_name="text-davinci-003", openai_api_key=openai_api_key, temperature=0
    ),
    prompt=prompt,
    verbose=True,
    memory=memory,
)

app = Flask(__name__)


@app.route("/chat", methods=["POST"])
def chat():
    recipient = request.form.get("From")
    message = request.form.get("Body")

    # Load up the specific user chat history
    try:
        history = PostgresChatMessageHistory(
            session_id=recipient,
            connection_string="postgresql://postgres:g9wW6vVVFjF5ZSEFytXL@containers-us-west-67.railway.app:7803/railway",
            table_name="projectmemory",
        )
    except Exception as e:
        return str(e)

    dic = {"human_input": message, "chat_history": history.messages}
    reply = llm_chain.run(dic)

    # Send the reply back to the WhatsApp number
    response = MessagingResponse()
    response.message(reply)
    return str(response)


if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=5000))
