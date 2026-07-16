from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime, tool
import requests
from config.setting import API_KEY, MODEL
from services.model import model
from langgraph.checkpoint.memory import InMemorySaver


client = httpx.AsyncClient(timeout=10)
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


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





import httpx
from mcp.server.fastmcp import FastMCP
from config.setting import OPENWEATHERMAP_API_KEY

mcp = FastMCP("Weather")



tool()
async def get_weather(city: str) -> str:
    """Get the current weather for a city."""

    if not OPENWEATHERMAP_API_KEY:
        return "Weather API key is missing."

    try:
        response = await client.get(
            BASE_URL,
            params={
                "q": city,
                "appid": OPENWEATHERMAP_API_KEY,
                "units": "metric",
            },
        )

        response.raise_for_status()
        data = response.json()

        return (
            f"📍 {data['name']}, {data['sys']['country']}\n"
            f"🌤 {data['weather'][0]['description'].title()}\n"
            f"🌡 {data['main']['temp']}°C\n"
            f"🤗 Feels Like: {data['main']['feels_like']}°C\n"
            f"💧 Humidity: {data['main']['humidity']}%\n"
            f"💨 Wind: {data['wind']['speed']} m/s"
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"City '{city}' not found."

        return f"Weather service returned HTTP {e.response.status_code}."

    except httpx.RequestError as e:
        return f"Unable to reach the weather service: {e}"
    



if __name__ == "__main__":
    mcp.run(transport="streamable-http")