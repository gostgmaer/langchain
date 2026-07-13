from typing import Annotated
from urllib import response
from langchain.chat_models import init_chat_model
from sqlalchemy import true
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from services.model import model
from services.uicli import print_ai_response
from langgraph.checkpoint.memory import InMemorySaver
# llm = init_chat_model("google-genai:google-gemini-3.1-flash-lite")

import uuid

class State(TypedDict):
    messages: Annotated[list, add_messages]


def prompt_llm(state: State):
    response = model.invoke(state["messages"])

    return {"messages": [response]}


builder = StateGraph(State)

builder.add_node(prompt_llm)

builder.add_edge(START, "prompt_llm")
builder.add_edge("prompt_llm", END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
config = {'configurable': {'thread_id': str(uuid.uuid4())}}
while True:
    user_message = input("Ask a question: ")
    if user_message.lower() == "exit":
        break
    res = graph.invoke({"messages": [{"role": "human", "content": user_message}]}, config=config)
    print_ai_response(res)


