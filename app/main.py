from contextlib import asynccontextmanager
import logging

import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.redis import pool, redis_manager
from app.core.ws import websocket_conn_man
from app.core.db import initialize_tables
from app.core.postgres import db_pg as database, cavecad as cavecad_db

logger = logging.getLogger(__name__)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup items
    logger.info("Starting Redis listener...")
    await websocket_conn_man.start_listening()
    await database.connect()
    await redis_manager.init_pool()
    # await cavecad_db.connect()
    # await initialize_tables(database)
    yield

    # Shutdown works
    logger.info("Shutting down Redis listener...")
    await websocket_conn_man.stop_listening()
    await pool.disconnect()
    await database.disconnect()
    # await cavecad_db.disconnect()

    # Close the main Redis pool if needed
    if hasattr(app.state, "redis_pool"):
        await app.state.redis_pool.disconnect()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://mnoytaspd1",
        "https://mnoytaspd1",
        "http://mnoytaspd1:3001",
        "https://mnoytaspd1:3001",
        "http://fragmentation-frontend:3000",
        "https://fragmentation-frontend:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
