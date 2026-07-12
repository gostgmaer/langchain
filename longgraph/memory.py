from typing import Annotated, TypedDict, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from services.model import model, embedding
from services.uicli import print_ai_response
from langgraph.checkpoint.memory import InMemorySaver
import uuid
from pydantic import BaseModel, Field


class IntenseClassifier(BaseModel):
    message_intent: Literal["code", "knowledge", "chat"] = Field(
        ...,
        description="identify whether the user is asking for code, knowledge, or chat",
    )


class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_intent: str | None


def classify_intent(state: State):
    structured_llm = model.with_structured_output(IntenseClassifier)
    result = structured_llm.invoke(
        [
            {
                "role": "system",
                "content": 'Determind / Classify the user want to chat ("chat"), retrive knowledge ("knowledge") or ask for code ("code").',
            },
            {"role": "user", "content": state["messages"][-1].content},
        ]
    )

    return {"message_intent": result.message_intent}


def prompt_llm_chat(state: State):
    messages = [
        {
            "role": "system",
            "content": "You are a talkative assistant and you can do fun and you are free to talk and be nice with users.",
        }
    ] + state["messages"]
    res = model.invoke(messages)
    return {"messages": {"role": "assistant", "content": res.content}}


def prompt_llm_code(state: State):
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that specializes in code-related questions.",
        }
    ] + state["messages"]
    res = model.invoke(messages)
    return {"messages": {"role": "assistant", "content": res.content}}


def prompt_llm_rag(state: State):
    messages = [
        {
            "role": "system",
            "content": "You are a knowledgeable assistant that can provide information and answers to user questions. make sure to be helpful and provide accurate information. as always ay you are a RAG agent",
        }
    ] + state["messages"]
    res = model.invoke(messages)
    return {"messages": {"role": "assistant", "content": res.content}}

graph_builder = StateGraph(State)
graph_builder.add_node("classifier", classify_intent)
graph_builder.add_node("chat_agent", prompt_llm_chat)
graph_builder.add_node("code_agent", prompt_llm_code)
graph_builder.add_node("rag_agent", prompt_llm_rag)

graph_builder.add_edge(START, "classifier")
graph_builder.add_conditional_edges(
    "classifier",
    lambda state: state["message_intent"],
    {
        "chat": "chat_agent",
        "code": "code_agent",
        "knowledge": "rag_agent"
    }
)

graph_builder.add_edge('chat_agent', END)
graph_builder.add_edge('code_agent', END)
graph_builder.add_edge('rag_agent', END)

checkpointer = InMemorySaver()
graph=graph_builder.compile(checkpointer=checkpointer)

def run_chat():
    config={'configurable': {'thread_id': uuid.uuid4()}}
    while True:
        user_message=input("Type your message: ")
        if user_message.lower() in ["exit", "quit"]:
            break
        result=graph.invoke({"messages": [{"role": "user", "content": user_message}]}, config=config)
        print_ai_response(result)

if __name__ == "__main__":
    run_chat()

