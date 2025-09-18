import asyncio
import logging
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

import asyncpg
from asyncpg import Pool
from asyncpg.exceptions import PostgresError

from app.core.config import settings
import functools

logger = logging.getLogger(__name__)


class ProductionPostgres:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[Pool] = None
        self._connection_retries = 3
        self._retry_delay = 1.0

    async def connect(self):
        """Create connection pool with production-ready settings"""
        if self.pool is not None:
            logger.warning("Database pool already exists")
            return

        pool_config = {
            "dsn": self.database_url,
            "min_size": 10,  # Minimum connections in pool
            "max_size": 15,  # Maximum connections in pool
            "max_queries": 50000,  # Max queries per connection before recycling
            "max_inactive_connection_lifetime": 300.0,  # 5 minutes
            "timeout": 60.0,  # Connection timeout
            "command_timeout": 30.0,  # Query timeout
            "server_settings": {
                "jit": "off",  # Disable JIT for better performance on simple queries
                "application_name": "back-end-fragmentation",
            },
        }

        for attempt in range(self._connection_retries):
            try:
                self.pool = await asyncpg.create_pool(**pool_config)
                logger.info(
                    f"Database pool created successfully (attempt {attempt + 1})"
                )

                # Test the connection
                async with self.pool.acquire() as conn:
                    await conn.execute("SELECT 1")

                logger.info("Database connection test successful")
                return

            except Exception as e:
                logger.error(
                    f"Failed to create database pool (attempt {attempt + 1}): {e}"
                )
                if attempt < self._connection_retries - 1:
                    await asyncio.sleep(self._retry_delay * (2**attempt))
                else:
                    raise ConnectionError(
                        f"Failed to connect to database after {self._connection_retries} attempts"
                    )

    async def disconnect(self):
        """Gracefully close the connection pool"""
        if self.pool is not None:
            try:
                await self.pool.close()
                logger.info("Database pool closed successfully")
            except Exception as e:
                logger.error(f"Error closing database pool: {e}")
            finally:
                self.pool = None

    @asynccontextmanager
    async def get_connection(self):
        """Context manager for getting database connections"""
        if self.pool is None:
            raise RuntimeError("Database pool not initialized. Call connect() first.")

        connection = None
        try:
            connection = await self.pool.acquire()
            yield connection
        except PostgresError as e:
            logger.error(f"Database query error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            raise
        finally:
            if connection:
                await self.pool.release(connection)

    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results"""
        async with self.get_connection() as conn:
            try:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
            except PostgresError as e:
                logger.error(f"Query execution failed: {query[:100]}... Error: {e}")
                raise

    async def execute_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a SELECT query and return single result"""
        async with self.get_connection() as conn:
            try:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
            except PostgresError as e:
                logger.error(f"Query execution failed: {query[:100]}... Error: {e}")
                raise

    async def execute_command(self, query: str, *args) -> str:
        """Execute INSERT/UPDATE/DELETE and return status"""
        async with self.get_connection() as conn:
            try:
                result = await conn.execute(query, *args)
                return result
            except PostgresError as e:
                logger.error(f"Command execution failed: {query[:100]}... Error: {e}")
                raise

    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            async with self.get_connection() as conn:
                await conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def transaction(self, func):
        async def decorator(*args, **kwargs):
            async with self.get_connection() as conn:
                async with conn.transaction():
                    try:
                        return await func(connection=conn, *args, **kwargs)
                    except PostgresError as e:
                        logger.error("Transaction failed with {e}")
                        raise

        return decorator

    @property
    def is_connected(self) -> bool:
        """Check if pool is initialized"""
        return self.pool is not None and not self.pool._closed


# Create singleton instance
db_pg = ProductionPostgres(str(settings.ASYNCPG_URL))
cavecad = ProductionPostgres(str(settings.CAVECAD_URL))
