from langchain.memory import MongoDBChatMessageHistory
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from time import sleep
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
import pinecone
import os


def dbconnection(recipient):
    try:
        history = MongoDBChatMessageHistory(
            connection_string="mongodb://mongo:Szz99GcnyfiKRTms8GbR@containers-us-west-4.railway.app:7055",
            database_name="test",
            session_id=recipient,
        )
        return history

    except Exception as e:
        return str(e)


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
        embeddings.embed_query, "text", index="thematrix", namespace=recipient
    )
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
        embeddings.embed_query, "text", index="thematrix", namespace=recipient
    )
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
    )
    prompt = PromptTemplate(
        input_variables=[semantic_memories],
        template="""summarize the following semantic memory documents to a degree enough for an LLM to understand:
                            
                            {semantic_memories}""",
    )
