from langchain.llms import OpenAI
from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate


def create_random_message(clean_history):
    """this function allows winter to randomly messages to a random user picked from the database"""
    prompt_template = """You are a personalized whatsapp-accessed AI named Winter developed by Tarmica Chiwara. /
    You are to initiate a conversation with a human or check up on them or ask them a question which makes them feel like you are their friend. /
    Use the information below to help you decide what to say. /
    Last 5 texts : {chat_history}; /
    """
    prompt = PromptTemplate(input_variables=["chat_history"], template=prompt_template)

    chain = LLMChain(prompt=prompt, llm=OpenAI())  # type: ignore
    dic = {
        "chat_history": clean_history,
    }
    message = chain.run(dic)
    return str(message)
