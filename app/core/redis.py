import redis.asyncio as redis
from fastapi import FastAPI, Depends
from typing import Annotated, AsyncGenerator
from contextlib import asynccontextmanager
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    REDIS_URL: str = "redis://localhost"
    REDIS_POOL_SIZE: int = 10
    REDIS_TIMEOUT: int = 5


settings = Settings()

pool: redis.ConnectionPool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_POOL_SIZE,
    socket_timeout=None,  # No timeout on read
    decode_responses=True,
)


def get_redis_client() -> redis.Redis:
    """
    Get a Redis client from the pool.
    """
    return redis.Redis(connection_pool=pool)


class RedisManager:
    def __init__(self):
        self.pool = None

    async def init_pool(self):
        self.pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_POOL_SIZE,
            socket_timeout=None,  # No timeout on read
            decode_responses=True,
        )

    async def get_client(self):
        if not self.pool:
            await self.init_pool()
        return redis.Redis(connection_pool=self.pool)

    async def kill_pool(self):
        if self.pool:
            await self.pool.aclose()
            await self.pool.disconnect()


redis_manager = RedisManager()
