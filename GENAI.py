from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.prebuilt import ToolNode, tools_condition
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, add_messages
from Tools import (minimax_AI)
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from datetime import datetime
import time

from dotenv import load_dotenv
load_dotenv()


llm = init_chat_model(
    "hermes3",
    model_provider="ollama",
    base_url="http://localhost:11434"
)


db_url = "postgresql://postgres:password@localhost:5432/postgres"
con_kwgs = {
    "autocommit": True,
    "row_factory": dict_row
}

class State(TypedDict):
    messages: Annotated[list, add_messages]

llm_with_tools = llm.bind_tools([minimax_AI])

def chatbot(state: State):
    messages = [
        SystemMessage(
            content=
            f"""
            Ask follow-up questions when information is missing.
            If the user changes the topic or want to talk about something else then don't take the context memory into consideration until it relates with the topic in anyway. 
            Just answer the question."""
        )
    ] + state ["messages"] 
    return {"messages": [llm_with_tools.invoke(messages)]}

builder = StateGraph(State)
builder.add_node(chatbot)
builder.add_node("tools", ToolNode([minimax_AI]))

builder.add_edge(START, "chatbot")
builder.add_conditional_edges("chatbot", tools_condition)
builder.add_edge("tools", "chatbot")

with ConnectionPool(conninfo=db_url, max_size=10, kwargs=con_kwgs) as pool:
    cp = PostgresSaver(pool)
    cp.setup()
    graph = builder.compile(checkpointer=cp)
    config = {'configurable': {'thread_id':889096}}

    while True:
        time1 = datetime.now().isoformat()
        msg1 = input("\nYou: ")
        if msg1 in {"exit", "goodbye", "bye"}:
            break
        msg = [msg1, time1]
        print("Gemini: ", end="", flush=True)
        state = graph.stream(
            {"messages": [{"role":"user","content":msg}]}, 
            config=config,
            stream_mode="updates"
        )
        for chunk in state:
            if "chatbot" in chunk:
                node_message = chunk["chatbot"]["messages"][-1]
                if hasattr(node_message, 'content') and node_message.content:
                    for char in node_message.content:
                        print(char, end="", flush= True)
                        time.sleep(0.01)
        print()