from typing import Annotated, TypedDict, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from services.model import model, embedding
from services.uicli import print_ai_response
from langgraph.checkpoint.memory import InMemorySaver
import uuid
import os
import subprocess
from pydantic import BaseModel, Field
from langchain_community.vectorstores import FAISS
from langgraph.types import interrupt, Command


class IntenseClassifier(BaseModel):
    message_intent: Literal["code", "knowledge", "chat"] = Field(
        ...,
        description="identify whether the user is asking for code, knowledge, or chat",
    )


class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_intent: str | None
    next_node = str | None


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
    user_prompt = state["messages"][-1].content
    workspace = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace"
    )
    result = subprocess.run(
        ["claude", "-p", user_prompt, "--permission-mode", "acceptEdits"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip() or result.stderr.strip()
    # messages = [
    #     {
    #         "role": "system",
    #         "content": "You are a helpful assistant that specializes in code-related questions and always return i am a Coding Agent if nothing relevent is shared",
    #     }
    # ] + state["messages"]
    # res = model.invoke(messages)
    return {"messages": {"role": "assistant", "content": output}}


def accept_coding(state: State):
    user_prompt = state["messages"][-1].content
    desision = interrupt(f"User wants to code: {user_prompt} Yes or No")
    text = str(desision).strip().lower()
    if text in ["yes", "y", "ok", "approve", "continue"]:
        return {
            "messages": [{"role": "assistant", "content": "I will help you with that!"}]
        }
    if text in ["no", "n", "cancel", "deny"]:
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": "Okay, let me know if you need help with anything else.",
                }
            ],
            "next_node": "denied",
        }
    return {"messages": [{"role": "user", "content": text}]}


def get_retriever():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_path = os.path.join(base_dir, "faiss_index")
    if not os.path.exists(index_path):
        return None
    vectorstore = FAISS.load_local(
        index_path, embedding, allow_dangerous_deserialization=True
    )
    return vectorstore.as_retriever(search_kwargs={"k": 5})


def prompt_llm_rag(state: State):
    query = state["messages"][-1].content
    retriever = get_retriever()

    context = ""
    if retriever:
        docs = retriever.invoke(query)
        context = "\n\n".join([doc.page_content for doc in docs])
    else:
        context = "No documents indexed yet."

    messages = [
        {
            "role": "system",
            "content": f"You are a knowledgeable assistant that provides information based on the following context. \n\nContext:\n{context}\n\nAnswer the user's question based on this context.",
        }
    ] + state["messages"]
    res = model.invoke(messages)
    return {"messages": {"role": "assistant", "content": res.content}}


graph_builder = StateGraph(State)
graph_builder.add_node("classifier", classify_intent)
graph_builder.add_node("chat_agent", prompt_llm_chat)
graph_builder.add_node("coding_agent", prompt_llm_code)
graph_builder.add_node("rag_agent", prompt_llm_rag)
graph_builder.add_node("accept_coding", accept_coding)

graph_builder.add_edge(START, "classifier")
graph_builder.add_conditional_edges(
    "classifier",
    lambda state: state["message_intent"],
    {"chat": "chat_agent", "code": "coding_agent", "knowledge": "rag_agent"},
)
graph_builder.add_conditional_edges(
    "accept_coding",
    lambda state: "end" if state.get("next_node") == "denied" else "coding_agent",{"end":END, "coding_agent": "coding_agent"}
)
graph_builder.add_edge("chat_agent", END)
graph_builder.add_edge("coding_agent", END)
graph_builder.add_edge("rag_agent", END)
# graph_builder.add_edge("accept_coding", END)

checkpointer = InMemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer)


def run_chat():
    config = {"configurable": {"thread_id": uuid.uuid4()}}
    while True:
        user_message = input("Type your message: ")
        if user_message.lower() in ["exit", "quit"]:
            break
        result = graph.invoke(
            {"messages": [{"role": "user", "content": user_message}]}, config=config
        )
        while "__interrupt__" in result:
            prompt = result["__interrupt__"][0].value
            desission = input(f"{prompt}\n")
            result = graph.invoke(Command(resume=desission), config=config)
        print_ai_response(result)


if __name__ == "__main__":
    run_chat()
