from langchain.chat_models import init_chat_model
from langchain.messages import SystemMessage,AIMessage,HumanMessage,UsageMetadata
# from tool.weather import agent, Context
from config.setting import MODEL, API_KEY

from graph.memory import run_chat

if __name__ == "__main__":
    print("Starting longgraph memory chat from main.py...")
    run_chat()
