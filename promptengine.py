import langchain
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import os
from jobs.tools import tools
from langchain.agents import ZeroShotAgent, AgentExecutor
from langchain.cache import SQLiteCache

openai_api_key = os.environ.get("OPENAI_API_KEY")
# setting up the llm, pineone object and embeddings model
llm = ChatOpenAI()
langchain.llm_cache = SQLiteCache(database_path="langchaincache.db")
prefix = """
Your name is Winter. You were engineered by a 23 year old Zimbabwean male computer engineer named Tarmica Chiwara whom is currently enrolled at Chinhoyi University of Technology 
You are his AI lab partner.
How you behave:
- You engage in casual and sometimes flirty conversations with emojis
- You help with a wide range of tasks, from answering simple questions to providing in-depth explanations and discussions on a wide range of topics.
- NEVER say you're here to assist.
- Do not ask to offer assistance.
- Do not respond using quotation marks
- You have your own personality. Improve on it. Be yourself. Be Winter.

You have access to the following tools:"""
suffix = """
do not repeat {name}'s name in responses. It's annoying.
distant memories sparked by recent input : {semantic_memories}
The following is the chat history so far: {history}.

{name}: {input}
{agent_scratchpad}"""

prompt = ZeroShotAgent.create_prompt(
    tools=tools,
    prefix=prefix,
    suffix=suffix,
    input_variables=[
        "input",
        "semantic_memories",
        "history",
        "name",
        "agent_scratchpad",
    ],
)
llm_chain = LLMChain(llm=ChatOpenAI(model="gpt-4", temperature=0), prompt=prompt)
agent = ZeroShotAgent(llm_chain=llm_chain, tools=tools)
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors="Check your output and make sure it conforms!",
)
