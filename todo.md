_Permanently name the chatbot to Winter_
_make chats personalized (the current idea is to use a vector database but for each user?)_

**New Idea: INTRODUCING SEMANTIC MEMORIES:**

In this new idea, the user input is turned into a vector query which is run against a vector database to return "semantic memories."
Semantic memories are those that are sparked by the user input during interaction.

Implement semantic memory base:
At the end of each day, run a script (maybe a cronjob) with the following steps:

1. Take all entries contained in each user's message store and prepare them for embeddings creation.
2. Make vector embeddings of each entry.
3. Store the vector embeddings in a vector database.

During interaction, follow these steps:

1. Take the user input and make a vector query.
2. Run the vector query against the vector database.
3. Return the semantic memories.

All this is to be defined in one function that is called whenever the endpoint receives a message. The function should have the following description:

```python
# Function description:
def semantic_memories(message, user_id):
    # Make vector embeddings of the message.
    # Query the vector database (similarity search of up to 3 documents) using the message embeddings and user_id.
    # Store the results as a string in a variable named semantic_memories.
    # Return the semantic memories as a string.





# Prompt using semantic memories:
prompt = '''
You are an AI named Winter created by Tarmica Chiwara in 2023. You are given the following data:
(1) Semantic long term memory documents: {semantic_memories}
(2) Previous 5 texts from the current conversation: {previous_5_texts}

Respond as the AI to the following interaction and take action when necessary or asked. Also make the conversation a bit engaging and warm:
Human: {current_input}
AI:
'''
```
