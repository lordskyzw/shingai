import os
from flask import Flask, render_template
from twilio.twiml.messaging_response import MessagingResponse
import openai
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain import PromptTemplate

openai.api_key = os.environ.get("OPENAI_API_KEY")


def process_audio(audio_data):
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt="Whisper:\n" + audio_data.decode(),
        max_tokens=1024,
        temperature=0.5,
    )
    return response.choices[0].text.strip()


template = """You are a chatbot having a conversation with a human.

{chat_history}
Human: {human_input}
Chatbot:"""

prompt = PromptTemplate(
    input_variables=["chat_history", "human_input"], template=template
)
memory = ConversationBufferMemory(memory_key="chat_history")

llm_chain = LLMChain(
    llm=OpenAI(
        model_name="text-davinci-003", openai_api_key=openai_api_key, temperature=0.7
    ),
    prompt=prompt,
    verbose=True,
    memory=memory,
)


app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    response = MessagingResponse()
    recipient = request.form.get("From")
    message = request.form.get("Body")
    audio_file = request.files.get("MediaUrl0")
    if not message and not audio_file:
        response.message("Sorry, I did not receive a message or audio from you.")
    else:
        if audio_file:
            audio_data = audio_file.read()
            reply = process_audio(audio_data)
        else:
            reply = llm_chain.predict(human_input=message)
        response.message(reply)
    return str(response)


if __name__ == "__main__":
    app.run(port=5002)
