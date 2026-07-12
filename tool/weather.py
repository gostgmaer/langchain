from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime, tool
import requests
from config.setting import API_KEY, MODEL
from services.model import model
from langgraph.checkpoint.memory import InMemorySaver


@dataclass
class WeatherData:
    city: str
    temperature: float
    description: str


@dataclass
class Context:
    user_id: str
    city: str


@dataclass
class ResponseFormat:
    summary: str
    temperature_celsius: float
    temperature_fahrenheit: float
    humidity: float


@tool(
    "get-weather",
    description="Get the current weather for a given location.",
    return_direct=False,
)
def get_weather(city: str):
    res = requests.get(f"https://wttr.in/{city}?format=j1")
    data = res.json()
    return WeatherData(
        city=city,
        temperature=data["current_condition"][0]["temp_C"],
        description=data["current_condition"][0]["weatherDesc"][0]["value"],
    )


@tool("locate-user", description="Locate the user by their ID.", return_direct=False)
def locate_user(runtime: ToolRuntime[Context]):
    # Placeholder implementation - replace with actual user location logic
    match runtime.context.user_id:
        case "user1":
            return Context(user_id=runtime.user_id, city="New York")
        case "user2":
            return Context(user_id=runtime.user_id, city="Los Angeles")
        case "user3":
            return Context(user_id=runtime.user_id, city="Chicago")
        case "user4":
            return Context(user_id=runtime.user_id, city="New Delhi")
        case _:
            return Context(user_id=runtime.user_id, city="New York")


        # model = init_chat_model(
        #     MODEL, model_provider="google_genai", api_key=API_KEY, temperature=0.7
        # )
checkpointer = InMemorySaver()

agent = create_agent(
    model=model,
    tools=[get_weather, locate_user],
    system_prompt="You are helpful Weather Assistant, Who provides accurate weather information.",
    context_schema=Context,
    checkpointer=checkpointer,
    response_format=ResponseFormat,
)
# config = {"configurable": {"thread_id": "1"}}

# response = agent.invoke(
#     {"message": [{"role": "user", "content": "What is the weather like in New York?"}]},
#     config=config,
#     context=Context(user_id="user1", city="New York"),
# )
# print(response["structured_response"])
# print(response["structured_response"].summery)
# print(response["structured_response"].temperature_cencius)
