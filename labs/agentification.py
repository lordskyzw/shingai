import os
from langchain.llms import OpenAI
import openai
import requests
from langchain.chains import LLMMathChain
from langchain.agents import Tool
from langchain.utilities import SerpAPIWrapper
from langchain.memory import ConversationBufferWindowMemory, MongoDBChatMessageHistory
from langchain.agents import initialize_agent


class Artist:
    def paint(self, prompt: str):
        """this function returns the uuid of the generated image"""
        response = openai.Image.create(prompt=prompt, n=1)
        return response["data"][0]["url"]


class WebGallery:
    def __init__(self):
        self.api_key = os.environ.get("SERP_API_KEY")
        self.base_url = "https://serpapi.com/search?engine=google_images"

    def search(self, query):
        parameters = {"q": query, "engine": "google_images", "api_key": self.api_key}
        response = requests.get(self.base_url, params=parameters)
        response = response.json()
        return response["images_results"][0]["original"]


llm = OpenAI(
    openai_api_key=os.environ.get("OPENAI_API_KEY"),
    temperature=0,
    model_name="gpt-4",  # type: ignore
)  # type: ignore


search = SerpAPIWrapper(serpapi_api_key=os.environ.get("SERP_API_KEY"))  # type: ignore
artist = Artist()
llm_math = LLMMathChain.from_llm(llm=llm)
image_search = WebGallery()


# intitialize the math tool
math_tool = Tool(
    name="Calculator",
    func=llm_math.run,
    description="useful for when you need math answers",
)

search_tool = Tool(
    name="Search",
    func=search.run,
    description="useful for when you need to search the web for current events, other information or time",
)

image_search_tool = Tool(
    name="ImageSearch",
    func=image_search.search,
    description="useful for when you need to search for an image from the web",
)

image_creation_tool = Tool(
    name="Image Creation",
    func=artist.paint,
    description="useful for when you need to create an image",
)


tools = [math_tool, search_tool, image_creation_tool, image_search_tool]

memory = ConversationBufferWindowMemory(
    chat_memory=MongoDBChatMessageHistory(
        connection_string="mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055",
        session_id="263778281345",
    ),
    memory_key="chat_history",  # type: ignore,
    ai_prefix="Winter",
    human_prefix="Tarmica",
)

agent = initialize_agent(
    agent="conversational-react-description",  # type: ignore
    memory=memory,  # type: ignore
    tools=tools,
    llm=llm,
    verbose=True,
)  # type: ignore
