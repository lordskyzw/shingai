import os
import psycopg2
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain import PromptTemplate
from langchain.memory.chat_message_histories import PostgresChatMessageHistory

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

# Initialize Postgres connection
db_url = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(db_url, sslmode="require") if db_url else None

# Define table schema
table_schema = """
CREATE TABLE IF NOT EXISTS projectmemory (
    id SERIAL PRIMARY KEY,
    number TEXT NOT NULL,
    history TEXT NOT NULL,
    data BYTEA NOT NULL
);
"""
# Create table if it does not exist
if conn:
    with conn.cursor() as cur:
        cur.execute(table_schema)
        conn.commit()

app = Flask(__name__)

@app.route("/chat", methods=["POST"])
def chat():
    response = MessagingResponse()
    recipient = request.form.get("From")
    message = request.form.get("Body")

    # Load up the specific user chat history
    history = PostgresChatMessageHistory(
        connection_string="postgresql://postgres:mypassword@localhost/chat_history",
        table_name="projectmemory",
        session_id=recipient,
    )
    
    try:
        dic = {"human_input": message, "chat_history": history.messages}
    except Exception as e:
        response.message(str(e))

    reply = llm_chain.run(dic)
    response.message(reply)
    return "200"

if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=5000))
