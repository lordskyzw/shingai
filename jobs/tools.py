import os
import requests
from time import sleep
import openai
import pinecone
import logging
from langchain.memory import MongoDBChatMessageHistory
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMMathChain
from langchain.agents import Tool
from langchain.utilities import SerpAPIWrapper
from pymongo import MongoClient
from sqlchain import db_chain

token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
phone_number_id = os.environ.get("PHONE_NUMBER_ID")
v15_base_url = "https://graph.facebook.com/v17.0"


class Artist:
    def paint(self, prompt: str):
        """this function returns the uuid of the generated image"""
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="512x512",
        )
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


class GraphicDesigner:
    """this class implements a designer API"""


class DocumentWriter:
    """this class writes/edits documents"""


llm = ChatOpenAI(
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

database_tool = Tool(
    name="DatabaseAgent",
    func=db_chain.run,
    description="useful for when you need to search through Kimtronix catalogue and return answers on what Kimtronix offers",
)

tools = [math_tool, search_tool, image_search_tool, database_tool]


########################################  history retrieval functions  ########################################
def get_recipient_chat_history(recipient):
    try:
        history = MongoDBChatMessageHistory(
            connection_string="mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055",
            database_name="test",
            session_id=str(recipient),
        )
        return history

    except Exception as e:
        return str(e)


def clean_history(history):
    """does string operations to clean the history therefore reducing the size of the prompt sent to the llm"""
    clean_history = str(history.messages[-8:]).replace(
        ", additional_kwargs={}, example=False", ""
    )
    clean_history = clean_history.replace("content=", "")
    clean_history = clean_history.replace(r"(lc_kwargs={", "")
    clean_history = clean_history.replace(r", 'additional_kwargs': {}", "")
    return clean_history


######################################## users database functions ########################################
def recipients_database():
    """users' database connection object"""
    client = MongoClient(
        "mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055"
    )
    database = client["users"]
    collection = database["recipients"]
    return collection


#########################################  semantic memories functions  ########################################


def create_or_update_semantic_memories(recipient):
    """the function to run at the end of the day"""
    # initialize pinecone index
    pinecone.init()
    index = pinecone.Index(index_name="thematrix")
    # make mongodb connection and create vector embeddings from the results got from querying the mongodb
    history = MongoDBChatMessageHistory(
        connection_string="mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055",
        database_name="test",
        session_id=recipient,
    )
    history_string = str(history.messages)
    # create vector embeddings object
    embeddings = OpenAIEmbeddings()
    # create vectorstore object
    vectorstore = Pinecone(
        embeddings.embed_query, "text", index="thematrix", namespace=recipient  # type: ignore
    )  # type: ignore
    vector_embeddings = [
        [0.2, 0.4, -0.1, 0.8, -0.5],
        [-0.3, 0.6, 0.9, -0.2, 0.1],
        [0.7, -0.5, 0.3, 0.1, -0.9],
    ]

    index.upsert(vectors=vector_embeddings, namespace=recipient)
    sleep(5)
    try:
        vectorstore.add_texts(texts=history_string, namespace=recipient)
        print(f"added or updated: {recipient} to vectordb")
    except Exception as e:
        raise RuntimeError(
            "An error occurred while adding texts to the vector store."
        ) from e


def get_semantic_memories(message, recipient):
    # create vector embeddings object
    embeddings = OpenAIEmbeddings()
    # create vectorstore object
    vectorstore = Pinecone(
        embeddings.embed_query, "text", index="thematrix", namespace=recipient  # type: ignore
    )  # type: ignore
    # get semantic results
    try:
        semantic_results = vectorstore.similarity_search(query=message, k=5)
        return str(semantic_results)
    except Exception:
        return None


def summarize_memories(semantic_memories):
    llm = OpenAI(
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        model="gpt-3.5-turbo",
        temperature=0,
    )
    prompt = PromptTemplate(
        input_variables=[semantic_memories],
        template="""summarize the following semantic memory documents to a degree enough for an LLM to understand:
                            
                            {semantic_memories}""",
    )


#############################################################################################################################################
########################################### CUSTOM WINTER FUNCTIONS #########################################################################
def mark_as_read_by_winter(message_id: str):
    """
    Marks a message as read

    Args:
        message_id[str]: Id of the message to be marked as read

    Returns:
        Dict[Any, Any]: Response from the API

    Example:
        >>> from whatsapp import WhatsApp
        >>> whatsapp = WhatsApp(token, phone_number_id)
        >>> whatsapp.mark_as_read("message_id")
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    json_data = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    logging.info(f"Marking message {message_id} as read")
    requests.post(
        f"{v15_base_url}/{phone_number_id}/messages",
        headers=headers,
        json=json_data,
    ).json()


def check_id_database(message_stamp: str):
    """Check if a message_stamp(combination of conersation_id+message_id) is in the database or not."""
    # users' database connection object
    client = MongoClient(
        "mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055"
    )
    database = client["Readit"]
    collection = database["messageids"]

    # Query the collection to check if the message_id exists
    query = {"message_stamp": message_stamp}
    result = collection.find_one(query)

    # Close the database connection
    client.close()

    # If the result is not None, the message_id exists in the database
    return result is not None


def add_id_to_database(message_stamp: str):
    """Add a message_stamp to the database."""
    # users' database connection object
    client = MongoClient(
        "mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055"
    )
    database = client["Readit"]
    collection = database["messageids"]

    # Create a document with the message_stamp and insert it into the collection
    document = {"message_stamp": message_stamp}
    collection.insert_one(document)

    # Close the database connection
    client.close()
