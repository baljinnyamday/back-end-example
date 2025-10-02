import json
import uuid
from typing import Annotated
from unittest.mock import Base

from bs4 import BeautifulSoup
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

from app.core.config import settings
from app.core.redis import get_redis_client
from app.core.ws import websocket_conn_man

router = APIRouter(prefix="/ws", tags=["Websocket"])


@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    user_id = str(uuid.uuid4())
    try:
        await websocket_conn_man.connect(websocket, user_id)

        while True:
            data = await websocket.receive_text()
            await websocket_conn_man.broadcast(f"Client #{user_id} says: {data}")

    except WebSocketDisconnect:
        print(f"User disconnected: {user_id}")
        websocket_conn_man.disconnect(user_id)
    except Exception as e:
        print(f"Error in websocket connection for {user_id}: {e}")
        websocket_conn_man.disconnect(user_id)


@router.websocket("/test")
async def websocket_endpoint_test(websocket: WebSocket):
    user_id = str(uuid.uuid4())
    try:
        await websocket_conn_man.connect(websocket, user_id)

        while True:
            data = await websocket.receive_text()
            await websocket_conn_man.broadcast(f"Client #{user_id} says: {data}")

    except WebSocketDisconnect:
        print(f"User disconnected: {user_id}")
        websocket_conn_man.disconnect(user_id)
    except Exception as e:
        print(f"Error in websocket connection for {user_id}: {e}")
        websocket_conn_man.disconnect(user_id)


@router.get("/all-connections")
async def get_all_connections():
    connections = websocket_conn_man.active_connections.copy()
    return {"connections": list(connections.keys())}


@router.get("/publish-test/{message}")
async def publish_test(message: str):
    redis_client = get_redis_client()
    response = await redis_client.publish(settings.SUBSCRIBED_CHANNEL, message)
    return {"message": message}


class TestOutput(BaseModel):
    biggest_city: str
    name_of_country: str
    population: int
    interesting_fact: Annotated[
        str, Field(description="Interesting fact about the country in 50 words")
    ]


@router.post("/send-message-force")
async def send_message():
    message = "This is a forced broadcast message."
    agent = Agent(
        "openai:gpt-4",
        instructions=("You will help user with their requests."),
        output_type=list[TestOutput],
    )

    async with agent.run_stream(
        "Tell me 10 interesting facts about countries"
    ) as stream:
        async for chunk in stream.stream_output(debounce_by=0.01):
            result = []
            for item in chunk:
                print(item)
                result.append(
                    {
                        "biggest_city": item.biggest_city or "N/A",
                        "name_of_country": item.name_of_country or "N/A",
                        "population": item.population or 0,
                        "interesting_fact": item.interesting_fact or "N/A",
                    }
                )

            await websocket_conn_man.broadcast(json.dumps(result))

    return {"message": message}
