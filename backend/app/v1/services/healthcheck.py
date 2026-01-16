"""Retail Product Agent Backend Healthcheck Services Module."""

import redis.asyncio as redis
from fastapi import APIRouter
from httpx import AsyncClient, HTTPError, TimeoutException

from app.v1.core.configurations import get_settings

router = APIRouter()
settings = get_settings()


async def get_redis_keys(pattern: str = "*", limit: int = 100) -> list[str] | list[dict]:
    """Retrieve Redis Keys."""
    redis_keys = []

    if not settings.redis_url:
        return [{"error": "Redis URL not configured"}]

    try:
        client = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=5.0)

        async with client:
            cursor, keys = await client.scan(cursor=0, match=pattern, count=limit)
            redis_keys = keys

        return redis_keys

    except (HTTPError, TimeoutException):
        return [{"error": "Could not connect to Redis"}]


async def get_qdrant_collections() -> list[str] | list[dict]:
    """Retrieve Qdrant collections."""
    qdrant_collections = []

    if not settings.qdrant_url:
        return [{"error": "Qdrant URL not configured"}]

    try:
        async with AsyncClient() as http_client:
            response = await http_client.get(f"{settings.qdrant_url}/collections", timeout=5.0)
            if response.status_code == 200:
                collections_data = response.json()
                for collection in collections_data.get("collections", []):
                    qdrant_collections.append(collection.get("name"))
        return qdrant_collections
    except (HTTPError, TimeoutException):
        qdrant_collections = [{"error": "Could not connect to Qdrant"}]
    return qdrant_collections
