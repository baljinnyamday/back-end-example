import uuid

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

from app.core.redis import get_redis_client
from app.core.ws import websocket_conn_man
from app.core.config import settings

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


@router.get("/all-connections")
async def get_all_connections():
    connections = websocket_conn_man.active_connections.copy()
    return {"connections": list(connections.keys())}


@router.get("/publish-test/{message}")
async def publish_test(message: str):
    redis_client = get_redis_client()
    response = await redis_client.publish(settings.SUBSCRIBED_CHANNEL, message)
    return {"message": message}
