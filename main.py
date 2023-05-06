import os
import requests
from flask import Flask, render_template, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse
import openai
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain import PromptTemplate
import tempfile

openai_api_key = os.environ.get("OPENAI_API_KEY")


def process_audio(audio_data):
    response = openai.Completion.create(
        engine="davinci-whisper-1",
        prompt="Whisper:\n" + audio_data.decode(),
        max_tokens=1024,
        temperature=0.5,
    )
    return response.choices[0].text.strip()


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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    voice_response = VoiceResponse()
    response = MessagingResponse()
    recipient = request.form.get("From")
    message = request.form.get("Body")
    audio_file = request.files.get("MediaUrl0")
    if not message and not audio_file:
        response.message("Sorry, I did not receive a message or audio from you.")
    else:
        if audio_file and not message:
            # Download the voice note data and save it to a temporary file
            with tempfile.TemporaryFile() as f:
                response = requests.get(audio_file)
                f.write(response.content)
                f.seek(0)
                audio_data = f.read()
                reply = process_audio(audio_data)
                voice_response.message(reply)
        else:
            reply = llm_chain.predict(human_input=message)
        response.message(reply)
    return str(response)


if __name__ == "__main__":
    app.run(port=5002)
