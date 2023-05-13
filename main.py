import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain import PromptTemplate
from langchain.memory.chat_message_histories import RedisChatMessageHistory

openai_api_key = os.environ.get("OPENAI_API_KEY")

template = """You are chatgpt having a conversation with a human.

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
    response = MessagingResponse()
    recipient = request.form.get("From")
    message = request.form.get("Body")

    # Load up the specific user chat history
    try:
        history = RedisChatMessageHistory(
            session_id=recipient,
            url="redis://default:STtIu6f9qhlcU97jfp9y@containers-us-west-110.railway.app:5859",
        )
    except Exception as e:
        response.message(str(e))

    dic = {"human_input": message, "chat_history": history.messages}
    reply = llm_chain.run(dic)
    response.message(reply)
    return str(reply)


if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=5000))
