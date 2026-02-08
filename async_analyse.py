"""Module for Asynchronous Ingestion of Product Data."""

import asyncio
import hashlib
from datetime import UTC, datetime
from io import BytesIO

import boto3
import numpy as np
import psycopg2
import requests
from botocore.exceptions import (
    ClientError,
    DataNotFoundError,
    NoCredentialsError,
    PartialCredentialsError,
)
from psycopg2.extras import Json
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from ingestion.config.settings import get_settings
from ingestion.utilities.embedding import create_image_from_url, embed_query
from ingestion.utilities.logger import setup_logger
from ingestion.utilities.scrape import scrape_stream

logger = setup_logger()
settings = get_settings()

COLLECTIONS: list[str] = settings.qdrant_collections.split(",")
ALLOWED_COLLECTIONS = ["jibbs_product_image_embeddings","jibbs_product_text_embeddings"]


def load_sql_file(
    file_path: str
    ) -> str:
    """Load SQL Query from a file."""
    with open(file_path) as file:
        sql_commands = file.read()
    return sql_commands


def run_sql_scripts(
    database_name: str,
    file_path: str) -> None:
    """Run SQL commands on the given PostgreSQL connection."""
    connection = get_postgres_connection(dbname=database_name)
    if connection is None:
        return
    try:
        cursor = connection.cursor()
        sql_commands = load_sql_file(file_path)
        cursor.execute(sql_commands)
        connection.commit()
        cursor.close()
    except psycopg2.Error as e:
        logger.error("Error executing SQL commands: %s", e)
        connection.rollback()


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
        if collection_name in created_collections or collection_name in ALLOWED_COLLECTIONS:
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


def upsert_embedding_data(connection: psycopg2.extensions.connection, embedding_data: dict) -> None:
    """Upsert embedding data into the PostgreSQL database table."""
    try:
        cursor = connection.cursor()
        upsert_query = """
        INSERT INTO embeddings (
            vector_id, product_id, product_image_index, product_s3_image_url,
            embedding_type, embedding_inserted_at, embedding_updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (vector_id) DO UPDATE SET
            product_image_index = EXCLUDED.product_image_index,
            product_s3_image_url = EXCLUDED.product_s3_image_url,
            embedding_updated_at = EXCLUDED.embedding_updated_at;
        """
        cursor.execute(
            upsert_query,
            (
                embedding_data["vector_id"],
                embedding_data["product_id"],
                embedding_data["product_image_index"],
                embedding_data["product_s3_image_url"],
                embedding_data["embedding_type"],
                embedding_data["embedding_inserted_at"],
                embedding_data["embedding_updated_at"],
            ),
        )
        connection.commit()
        cursor.close()
    except psycopg2.Error as e:
        logger.error("Error upserting embedding data: %s", e)
        connection.rollback()


def upsert_product_data(connection: psycopg2.extensions.connection, product_data: dict) -> None:
    """Upsert product data into the PostgreSQL database table."""
    try:
        cursor = connection.cursor()
        upsert_query = """
        INSERT INTO products (
            product_id, product_title, description, price, num_images,
            product_images, product_caption, product_s3_image_urls, financing, promo_tagline,
            sizes_available, product_url, product_category, product_inserted_at, product_updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (product_id) DO UPDATE SET
            price = EXCLUDED.price,
            num_images = EXCLUDED.num_images,
            product_images = EXCLUDED.product_images,
            product_caption = EXCLUDED.product_caption,
            product_s3_image_urls = EXCLUDED.product_s3_image_urls,
            financing = EXCLUDED.financing,
            promo_tagline = EXCLUDED.promo_tagline,
            sizes_available = EXCLUDED.sizes_available,
            product_url = EXCLUDED.product_url,
            product_category = EXCLUDED.product_category,
            product_updated_at = EXCLUDED.product_updated_at;
        """
        cursor.execute(
            upsert_query,
            (
                product_data["product_id"],
                product_data["product_title"],
                product_data["description"],
                product_data["price"],
                product_data["num_images"],
                product_data["product_images"],
                product_data["product_caption"],
                product_data["product_s3_image_urls"],
                Json(product_data["financing"]),
                product_data["promo_tagline"],
                product_data["sizes_available"],
                product_data["product_url"],
                product_data["product_category"],
                product_data["product_inserted_at"],
                product_data["product_updated_at"],
            ),
        )
        connection.commit()
        cursor.close()
    except psycopg2.Error as e:
        logger.error("Error upserting product data: %s", e)
        connection.rollback()


def generate_product_id(product_title: str) -> str:
    """Generate a product ID based on product title."""
    content = f"{product_title}"
    return int(hashlib.sha256(content.encode()).hexdigest(), 16) % (2**63)


def generate_vector_id(product_title: str, embedding_type: str, index: int | None = None) -> str:
    """Generate a vector ID based on product title."""
    content = f"{product_title}_{embedding_type}_{index}"
    return int(hashlib.sha256(content.encode()).hexdigest(), 16) % (2**63)


def get_s3_client(
    aws_access_key_id: str = settings.aws_access_key_id,
    aws_secret_access_key: str = settings.aws_secret_access_key,
    region_name: str = settings.aws_region,
):
    """
    Get S3 client.

    The S3 client is created using the provided AWS credentials and region.

    Incomplete or missing credentials will result in a logged error and a None return value.

    Args:
        aws_access_key_id (str): AWS access key ID.
        aws_secret_access_key (str): AWS secret access key.
        region_name (str): AWS region name.

    Returns:
        boto3.client: S3 client object.
    """
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )
        return s3_client
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.error("Credentials are not available or incomplete: %s", e)
        return None


def check_s3_bucket_exists(bucket_name: str) -> bool:
    """
    Check if an S3 bucket exists.

    Args:
        bucket_name (str): Name of the S3 bucket.

    Returns:
        bool: True if bucket exists, False otherwise.

    Raises:
        ClientError: If there is an error accessing S3.
        DataNotFoundError: If the bucket does not exist.
        NoCredentialsError: If S3 client could not be created due to missing credentials.
    """
    s3_client = get_s3_client()
    if s3_client is None:
        raise NoCredentialsError("S3 client could not be created due to missing credentials.")
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info("Bucket %s exists.", bucket_name)
        return True
    except (ClientError, DataNotFoundError) as e:
        logger.error("Bucket %s does not exist or is inaccessible: %s", bucket_name, e)
        return False


def create_s3_bucket(bucket_name: str) -> bool:
    """
    Create an S3 bucket.

    Args:
        bucket_name (str): Name of the S3 bucket to create.

    Returns:
        bool: True if bucket created successfully, False otherwise

    Raises:
        NoCredentialsError: If S3 client could not be created due to missing credentials.
        ClientError: If there is an error creating the bucket.
    """
    s3_client = get_s3_client()

    if s3_client is None:
        raise NoCredentialsError("S3 client could not be created due to missing credentials.")

    if check_s3_bucket_exists(bucket_name):
        return
    try:
        s3_client.create_bucket(Bucket=bucket_name)
        logger.info("Bucket %s created successfully.", bucket_name)
        return True
    except ClientError as e:
        logger.error("Failed to create bucket %s: %s", bucket_name, e)
        return False


def upload_file_to_s3(bucket_name: str, file_path: str, s3_key: str) -> bool:
    """
    Upload a file to an S3 bucket.
    Args:
        bucket_name (str): Name of the S3 bucket.
        file_path (str): Local path to the file to upload.
        s3_key (str): S3 object key (path in the bucket).

    Returns:
        bool: True if file uploaded successfully, False otherwise.

    Raises:
        NoCredentialsError: If S3 client could not be created due to missing credentials.
        ClientError: If there is an error uploading the file.
    """
    s3_client = get_s3_client()
    if s3_client is None:
        raise NoCredentialsError("S3 client could not be created due to missing credentials.")
    try:
        s3_client.upload_file(file_path, bucket_name, s3_key)
        logger.info("File %s uploaded to bucket %s as %s.", file_path, bucket_name, s3_key)
        return True
    except ClientError as e:
        logger.error("Failed to upload file %s to bucket %s: %s", file_path, bucket_name, e)
        return False


def upload_stream_to_s3(
    bucket_name: str, data_stream: BytesIO, product_id: str, image_index: int
) -> bool:
    """Uploads a file-like object (stream) to S3 without saving locally."""
    s3_client = get_s3_client()
    if s3_client is None:
        raise NoCredentialsError("S3 client missing.")
    try:
        data_stream.seek(0)
        s3_key = f"{product_id}/image_{image_index}.jpg"
        s3_client.upload_fileobj(data_stream, bucket_name, s3_key)
        s3_url = f"https://{bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
        return s3_url
    except ClientError as e:
        logger.error("Failed to upload stream: %s", e)
        return False


def get_product_images(bucket_name: str, product_id: str) -> list:
    """List all images for a given product ID in the specified S3 bucket."""
    s3_client = get_s3_client()
    if s3_client is None:
        raise NoCredentialsError("S3 client missing.")
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=f"{product_id}/")
        image_keys = []
        for page in page_iterator:
            for obj in page.get("Contents", []):
                image_keys.append(obj["Key"])
        return image_keys
    except ClientError as e:
        logger.error("Failed to list images for product %s: %s", product_id, e)
        return []


def stream_to_bytesio(data_stream) -> BytesIO:
    """Convert a stream to a BytesIO object."""
    bytes_io = BytesIO()
    for chunk in data_stream:
        bytes_io.write(chunk)
    bytes_io.seek(0)
    return bytes_io


def stream_image_to_bytesio(product_image_url) -> BytesIO:
    """Convert image stream to BytesIO object."""
    product_stream = requests.get(product_image_url, stream=True, timeout=10.0).raw
    product_bytesio = stream_to_bytesio(product_stream)
    return product_bytesio


def generate_image_caption(
    product_title: str,
    product_description: list[str],
    ) -> str:
    """
    Generate a product caption using the product title and description.

    Args:
        product_title (str): Title of the product.
        product_description (str): Description of the product.
    
    Returns:
        str: Generated product caption.
    """
    return f"{product_title}. {' '.join(product_description)}"


if __name__ == "__main__":
    import asyncio

    async def ingest_products():
        async for product in scrape_stream(
            categories=("jackets",),
            number_of_pages=1,
            limit_per_page=5
        ):
            product_id = generate_product_id(product["Product Title"].split("-")[0].strip())
            product_title = product["Product Title"].split("-")[0].strip()
            product_description = product.get("Product Details", [])
            product_caption = generate_image_caption(product_title, product_description)
            product_caption_embedding = embed_query(product_caption)
            product_data = {
                "product_id": product_id,
                "product_title": product_title,
                "description": product_description,
                "price": product.get("Product Price", ""),
                "num_images": product.get("No. of Images", 0),
                "product_images": product.get("Product Images", []),
                "product_caption": product_caption,
                "product_s3_image_urls": [],
                "financing": product.get("Financing", {}),
                "promo_tagline": product.get("Promo Tagline", ""),
                "sizes_available": product.get("Size Options", []),
                "product_url": product.get("Product URL", ""),
                "product_category": product.get("Product Category", ""),
                "product_inserted_at": datetime.now(UTC),
                "product_updated_at": datetime.now(UTC),
            }
            point = await create_point_with_metadata(
                embedding=product_caption_embedding,
                point_id=generate_vector_id(product_title, "text"),
                payload={
                    "product_id": product_id,
                    "num_images": product_data["num_images"],
                    "embedding_type": "text",
                }
            )
            await upsert_points(
                client=get_qdrant_client(),
                collection_name="jibbs_product_text_embeddings",
                points=[point]
            )
            upsert_product_data(
                connection=get_postgres_connection(),
                product_data=product_data
            )

            for image_index, product_image_url in enumerate(product.get("Product Images", [])):
                product_bytesio = stream_image_to_bytesio(product_image_url)
                s3_image_url = upload_stream_to_s3(
                    bucket_name="jibbs-test-catalog",
                    data_stream=product_bytesio,
                    product_id=product_id,
                    image_index=image_index,
                )
                product_image_embedding = embed_query(create_image_from_url(product_image_url))
                product_vector_id = generate_vector_id(product_title, "image", image_index)
                product_image_embedding_data = {
                    "vector_id": product_vector_id,
                    "product_id": product_id,
                    "product_image_index": image_index,
                    "product_s3_image_url": s3_image_url,
                    "embedding_type": "image",
                    "embedding_inserted_at": datetime.now(UTC),
                    "embedding_updated_at": datetime.now(UTC),
                }
                point = await create_point_with_metadata(
                    embedding=product_image_embedding,
                    point_id=product_vector_id,
                    payload={
                        "product_id": product_image_embedding_data["product_id"],
                        "product_s3_image_url": product_image_embedding_data["product_s3_image_url"],
                        "embedding_type": product_image_embedding_data["embedding_type"],
                    }
                )
                await upsert_points(
                    client=get_qdrant_client(),
                    collection_name="jibbs_product_image_embeddings",
                    points=[point]
                )
                upsert_embedding_data(
                    connection=get_postgres_connection(),
                    embedding_data=product_image_embedding_data
                )

    asyncio.run(ingest_products())
