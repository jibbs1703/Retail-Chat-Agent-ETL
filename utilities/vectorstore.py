"""Module for Managing the Vector Store."""

import numpy as np
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from config.settings import get_settings
from utilities.logger import setup_logger

logger = setup_logger("vectorstore.py")
settings = get_settings()

COLLECTIONS: list[str] = settings.qdrant_collections.split(",")
ALLOWED_COLLECTIONS = ["jibbs_product_image_embeddings", "jibbs_product_text_embeddings"]


def get_qdrant_client() -> AsyncQdrantClient:
    """Establish a Qdrant client connection."""
    client = AsyncQdrantClient(
        url=settings.qdrant_url,
    )
    logger.info("Successfully connected to Qdrant at: %s", settings.qdrant_url)
    return client


def validate_collection_name(
    collection_name: str, allowed_collections: list[str] = ALLOWED_COLLECTIONS
) -> bool:
    """Validate if the collection name is recognized."""
    return collection_name in allowed_collections


async def create_collection(collections: list[str] = COLLECTIONS) -> None:
    """Create Qdrant collections if they do not exist."""
    client = get_qdrant_client()
    try:
        created_collections = await client.get_collections()
        for collection_name in collections:
            if validate_collection_name(collection_name) and collection_name not in [
                collection.name for collection in created_collections.collections
            ]:
                await client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection: {collection_name}")
    finally:
        await client.close()


async def delete_collection(collection_name: str) -> None:
    """
    Delete a Qdrant Collection.

    Args:
        collection_name (str): Name of the collection to delete.

    Returns:
        None
    """
    client = get_qdrant_client()
    try:
        created_collections = await client.get_collections()
        if collection_name in created_collections or collection_name in ALLOWED_COLLECTIONS:
            await client.delete_collection(collection_name=collection_name)
    finally:
        await client.close()


async def create_point_with_metadata(
    embedding: np.ndarray, point_id: str, payload: dict | None = None
) -> PointStruct:
    """Create a Qdrant PointStruct from an embedding vector."""
    return PointStruct(id=point_id, vector=embedding.tolist(), payload=payload)


async def upsert_points(collection_name: str, points: list[PointStruct]) -> None:
    """Upsert points to Qdrant collection."""
    client = get_qdrant_client()
    if validate_collection_name(collection_name):
        logger.info("Collection name %s is valid.", collection_name)
        try:
            await client.upsert(collection_name=collection_name, points=points)
            logger.info(f"Upserted {len(points)} points to {collection_name}")
        finally:
            await client.close()
