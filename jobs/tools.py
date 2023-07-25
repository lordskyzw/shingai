from langchain.memory import MongoDBChatMessageHistory
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from time import sleep
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
import pinecone
import os
from pymongo import MongoClient
import logging
import requests


token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
phone_number_id = os.environ.get("PHONE_NUMBER_ID")
v15_base_url = "https://graph.facebook.com/v17.0"


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
    clean_history = str(history.messages[-14:]).replace(
        ", additional_kwargs={}, example=False", ""
    )
    clean_history.replace("content=", "")
    clean_history.replace(r"(lc_kwargs={", "")
    clean_history.replace(r", 'additional_kwargs': {}", "")
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
    embeddings = OpenAIEmbeddings()  # type: ignore
    # create vectorstore object
    vectorstore = Pinecone(
        embeddings.embed_query, "text", index="thematrix", namespace=recipient  # type: ignore
    )  # type: ignore
    vector_embeddings = [
        [0.2, 0.4, -0.1, 0.8, -0.5],
        [-0.3, 0.6, 0.9, -0.2, 0.1],
        [0.7, -0.5, 0.3, 0.1, -0.9],
    ]

    index.upsert(vectors=vector_embeddings, namespace=recipient)  # type: ignore
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
    embeddings = OpenAIEmbeddings()  # type: ignore
    # create vectorstore object
    vectorstore = Pinecone(
        embeddings.embed_query, "text", index="thematrix", namespace=recipient  # type: ignore
    )  # type: ignore
    # get semantic results
    try:
        semantic_results = vectorstore.similarity_search(
            query=message, k=5, namespace=recipient
        )
        return str(semantic_results)
    except Exception:
        return None


def summarize_memories(semantic_memories):
    llm = OpenAI(
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        model="gpt-3.5-turbo",
        temperature=0,
    )  # type: ignore
    prompt = PromptTemplate(
        input_variables=[semantic_memories],
        template="""summarize the following semantic memory documents to a degree enough for an LLM to understand:
                            
                            {semantic_memories}""",
    )


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
