import asyncio
from fastapi import WebSocket
import redis.asyncio as aioredis
from fastapi import WebSocket
from redis.asyncio.client import PubSub

from app.core.redis import get_redis_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.redis_client = get_redis_client()
        self.pubsub = self.redis_client.pubsub()
        self.channel = settings.SUBSCRIBED_CHANNEL
        self.listen_task = None
        self._shutdown_event = asyncio.Event()

    async def subscribe(self):
        await self.pubsub.subscribe(self.channel)

    async def unsubscribe(self):
        await self.pubsub.unsubscribe(self.channel)

    async def listen(self):
        """Listen for Redis messages and broadcast to WebSocket clients"""
        if not self.pubsub.subscribed:
            await self.subscribe()

        try:
            async for message in self.pubsub.listen():
                # Check if shutdown was requested
                if self._shutdown_event.is_set():
                    break

                if message["type"] == "message":
                    await self.broadcast(message["data"])
        except asyncio.CancelledError:
            logger.info("Redis listener task was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in listening to Redis channel: {e}")
        finally:
            logger.info("UNSUBSCRIBING FROM CHANNEL")
            await self.cleanup_redis()

    async def cleanup_redis(self):
        """Clean up Redis connections"""
        try:
            await self.unsubscribe()
            await self.pubsub.close()
            # Don't close the main redis_client here  it's used elsewhere
            # await self.redis_client.close()
        except Exception as e:
            logger.error(f"Error cleaning up Redis: {e}")

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()

        self.active_connections[user_id] = websocket

    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

    async def send_message(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

    async def start_listening(self):
        """Start the Redis listener task"""
        if self.listen_task is None or self.listen_task.done():
            self.listen_task = asyncio.create_task(self.listen())

    async def stop_listening(self):
        """Stop the Redis listener task"""
        self._shutdown_event.set()
        if self.listen_task and not self.listen_task.done():
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass


websocket_conn_man = ConnectionManager()
