from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
from langchain.agents import create_agent
import asyncio
from services.model import embedding, model


async def main():
    client = MultiServerMCPClient(
        {
            "math": {
                "command": "python",
                "args": ["-m", "mcp_server.calculatorServer"],
                "transport": "stdio",
            },
            "weather": {
                "transport": "streamable-http",
                "url": "http://localhost:8000/mcp",
            },
        }
    )

    tools = await client.get_tools()
    agent = create_agent(model, tools)

    math_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "What is 5 + 3 and multiply by 8?"}]}
    )
    print("Math Response:", math_response["messages"][-1].content)
    # print(math_response["messages"][-1].content)

    weather_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "What is the weather like in New York?"}]}
    )
    # print("Math Response:", math_response["messages"][-1].content)
    print(weather_response["messages"][-1].content)


asyncio.run(main())
