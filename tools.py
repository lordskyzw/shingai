from langchain.memory import MongoDBChatMessageHistory


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
