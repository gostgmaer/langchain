from langchain.agents import create_agent
from requests import request
from services.model import embedding, model
from langchain.agents.middleware import ModelRequest,ModelResponse,dynamic_prompt
from dataclasses import dataclass

from services.uicli import print_ai_response, stream_response



@dataclass
class Context:
    role:str


@dynamic_prompt
def user_role_prompt(request: ModelRequest) -> str:
    user_role=request.runtime.context.role
    base_prompt="You are a helpful assistant. with highly knowledge of the Universe."
    match user_role:
        case "export":
            return f'{base_prompt} You are an export specialist and return detailed information.'
        case "beginner":
            return f'{base_prompt} You are a beginner and need simple explanations.'
        case "child":
            return f'{base_prompt} You are a child and need age-appropriate explanations.'
        case _:
            return base_prompt
        

agent = create_agent(
    model=model,
    tools=[],
    middleware=[user_role_prompt],   # ✅
    context_schema=Context,
)


stream_response(
    agent,
    {
        "messages": [
            {
                "role": "human",
                "content": "Explain the concept of gravity."
            }
        ]
    },context=Context(role="export"),
)

# response = agent.invoke(
#     {
#         "messages": [
#             {
#                 "role": "human",
#                 "content": "Explain the concept of gravity."
#             }
#         ]
#     },context=Context(role="export")
# )

# print_ai_response(response)

    