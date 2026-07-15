import httpx
from mcp.server.fastmcp import FastMCP
from config.setting import OPENWEATHERMAP_API_KEY

mcp = FastMCP("Weather")

client = httpx.AsyncClient(timeout=10)
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


@mcp.tool()
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