from langchain.chat_models import init_chat_model
from langchain.messages import SystemMessage,AIMessage,HumanMessage,UsageMetadata
from tool.weather import agent, Context
from config.setting import MODEL, API_KEY


conversation = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="give me a 3500 word essay on the benefits of exercise and its impact on mental health. must be well-structured and include references. university level and highly detailed"),
]
# model_name = conversation.response_metadata.get("model_name", MODEL)
# response = model.stream(conversation)
# print(response.usage_metadata)
# print(response.response_metadata)
# print(response.content)

# # Extract text
# text = "".join(
#     block["text"]
#     for block in response.content
#     if block["type"] == "text"
# )




# print("\n" + text + "\n")
# print("-" * 100)
# print(
#     f"{response.usage_metadata}"
#     f"{'MODEL: ' + model_name:>40}"
# )
# full_response = None
# for chunk in model.stream(conversation):
#     print(chunk.text, end="", flush=True)

#     # Merge chunks
#     if full_response is None:
#         full_response = chunk
#     else:
#         full_response += chunk




# print("\n")
# print("=" * 100)
# print("Model :", full_response.response_metadata.get("model_name"))
# print("Usage :", full_response.usage_metadata)




config = {
    "configurable": {
        "thread_id": "1"
    }
}

response = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "What is the weather like in New York?"
            }
        ]
    },
    config=config,
    context=Context(
        user_id="user1",
        city="New York",
    ),
)

print(response["structured_response"])
print(response["structured_response"].summary)
print(response["structured_response"].temperature_celsius)