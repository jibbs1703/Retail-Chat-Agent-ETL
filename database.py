import asyncio
from io import BytesIO
from uuid import uuid4

import numpy as np
import psycopg2
import requests
from PIL import Image
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from ingestion.config.settings import get_settings
from ingestion.utilities.logger import setup_logger

logger = setup_logger(__file__)
settings = get_settings()

COLLECTIONS: list[str] = settings.qdrant_collections.split(",")
ALLOWED_COLLECTIONS = ["jibbs_product_image_embeddings","jibbs_product_text_embeddings"]


def load_sql_file(file_path: str) -> str:
    """Load SQL commands from a file."""
    with open(file_path) as file:
        sql_commands = file.read()
    return sql_commands


def get_qdrant_client() -> AsyncQdrantClient:
    """Establish a Qdrant client connection."""
    client = AsyncQdrantClient(
        url=settings.qdrant_url,
    )
    logger.info("Successfully connected to Qdrant at: %s", settings.qdrant_url)
    return client


def validate_collection_name(
    collection_name: str,
    allowed_collections: list[str] = ALLOWED_COLLECTIONS) -> bool:
    """Validate if the collection name is recognized."""
    return collection_name in allowed_collections


async def create_collection(
    client: AsyncQdrantClient,
    collections: list[str] = COLLECTIONS) -> None:
    """Create Qdrant collections if they do not exist."""
    try:
        created_collections = await client.get_collections()
        for collection_name in collections:
            if validate_collection_name(collection_name) and collection_name not in [
                collection.name
                for collection in created_collections.collections
            ]:
                await client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection: {collection_name}")
    finally:
        await client.close()


async def delete_collection(
    client: AsyncQdrantClient,
    collection_name: str
    ) -> None:
    """
    Delete a Qdrant Collection.

    Args:
        collection_name (str): Name of the collection to delete.

    Returns:
        None
    """
    try:
        created_collections = await client.get_collections()
        if collection_name in created_collections:
            await client.delete_collection(collection_name=collection_name)
    finally:
            await client.close()


async def create_point_with_metadata(
        embedding: np.ndarray,
        point_id: str,
        payload: dict | None = None
    ) -> PointStruct:
    """Create a Qdrant PointStruct from an embedding vector."""
    return PointStruct(
        id=point_id,
        vector=embedding.tolist(),
        payload=payload
    )


async def upsert_points(
        client: AsyncQdrantClient,
        collection_name: str,
       points: list[PointStruct]):
    """Upsert points to Qdrant collection."""
    if validate_collection_name(collection_name):
        logger.info("Collection name %s is valid.", collection_name)
        try:
            await client.upsert(collection_name=collection_name, points=points)
            logger.info(f"Upserted {len(points)} points to {collection_name}")
        finally:
            await client.close()


def get_postgres_connection(
    dbname: str = settings.postgres_database,
    user: str = settings.postgres_user,
    password: str = settings.postgres_password,
    host: str = settings.postgres_host,
    port: int = settings.postgres_port,
) -> psycopg2.extensions.connection:
    """Establish a postgres database connection."""
    try:
        connection = psycopg2.connect(
            dbname=dbname, user=user, password=password, host=host, port=port
        )
        logger.info("Successfully connected to database: %s", dbname)
        return connection
    except psycopg2.Error as e:
        logger.error("Error connecting to PostgreSQL database: %s", e)
        return None


def create_postgres_database(database_name: str) -> None:
    """Create PostgreSQL database if it does not exist."""
    connection = get_postgres_connection()
    if connection is None:
        return
    try:
        connection.autocommit = True
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE {database_name};")
        cursor.close()
        connection.close()
    except psycopg2.errors.DuplicateDatabase:
        pass
    except psycopg2.Error as e:
        logger.error("Error creating PostgreSQL database: %s", e)


def list_postgres_databases() -> list:
    """List all PostgreSQL databases."""
    connection = get_postgres_connection()
    databases = []
    if connection is None:
        return databases
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
    except psycopg2.Error as e:
        logger.error("Error listing PostgreSQL databases: %s", e)
    return databases


def run_sql_scripts(database_name: str, file_path: str) -> None:
    """Run SQL commands on the given PostgreSQL connection."""
    connection = get_postgres_connection(dbname=database_name)
    if connection is None:
        return
    try:
        cursor = connection.cursor()
        sql_commands = load_sql_file(file_path)
        cursor.execute(sql_commands)
        connection.commit()
        logger.info("Successfully executed SQL commands from %s", file_path)
        cursor.close()
    except psycopg2.Error as e:
        logger.error("Error executing SQL commands: %s", e)
        connection.rollback()


def create_image_from_url(image_url: str) -> Image.Image:
    """
    Create a PIL Image from a given image URL.

    Args:
        image_url (str): URL of the image to fetch.
    
    Returns:
        Image.Image: PIL Image object.
    Raises:
        ValueError: If the image cannot be fetched or opened.
    """
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGB")
        return image
    except Exception as e:
        logger.error(f"Error fetching image from URL {image_url}: {e}")
        raise ValueError(f"Could not create image from URL: {image_url}") from e
    

if __name__ == "__main__":
    # image_embedding = embed_query(image)
    # point = asyncio.run(create_point_with_metadata(
    #     embedding=image_embedding,
    #     point_id=str(uuid4()),
    #     payload={"product_id": "example_product_12345",
    #              "product_name": "Example Product Name",
    #              "product_category": "Example Category"}
    # ))
    # asyncio.run(upsert_points(
    #     client=get_qdrant_client(),
    #     collection_name="jibbs_product_image_embeddings",
    #     points=[point]
    # ))
    # client = get_qdrant_client()

    # asyncio.run(create_collection(client, COLLECTIONS))
    # asyncio.run(upsert_points(client, "wrong_collection", []))

    run_sql_scripts(settings.postgres_database, "queries/drop_products.sql")
    run_sql_scripts(settings.postgres_database, "queries/drop_embeddings.sql")

    run_sql_scripts(settings.postgres_database, "queries/create_products.sql")
    run_sql_scripts(settings.postgres_database, "queries/create_embeddings.sql")
