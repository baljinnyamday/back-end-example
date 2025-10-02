from bs4 import BeautifulSoup
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

# from .crawler import get_clean_markdown

class ReturnDep(BaseModel):
    url: str
    description:str

server = MCPServerStreamableHTTP("http://localhost:8931/mcp")

agent = Agent(
    "openai:gpt-4o",
    instructions=("You will browse web and help user with their requests."),
    toolsets=[server],
    output_type=list[ReturnDep],
)



async def main():
    result = await agent.run("Visit blog.balj.in and get all urls this website has")
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
