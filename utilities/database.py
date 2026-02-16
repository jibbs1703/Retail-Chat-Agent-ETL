"""Relational database utilities for PostgreSQL."""

import importlib.resources
import types
from io import BytesIO

import psycopg2
import requests
from PIL import Image
from psycopg2.extras import Json

from config.settings import get_settings
from utilities.logger import setup_logger

logger = setup_logger("database.py")
settings = get_settings()


def load_sql_file(module: types.ModuleType, filename: str) -> str:
    """Load SQL Query from a file."""
    file_path = importlib.resources.files(module) / filename
    with open(file_path) as file:
        sql_commands = file.read()
    return sql_commands


def run_sql_scripts(database_name: str, module: types.ModuleType, filename: str) -> None:
    """Run SQL commands on the given PostgreSQL connection."""
    connection = get_postgres_connection(dbname=database_name)
    if connection is None:
        return
    try:
        cursor = connection.cursor()
        sql_commands = load_sql_file(module, filename)
        cursor.execute(sql_commands)
        connection.commit()
        cursor.close()
    except psycopg2.Error as e:
        logger.error("Error executing SQL commands: %s", e)
        connection.rollback()
        connection.close()


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


def upsert_embedding_data(embedding_data: dict) -> None:
    """Upsert embedding data into the PostgreSQL database table."""
    connection = get_postgres_connection()
    if connection is None:
        raise ConnectionError("Failed to connect to the PostgreSQL database.")
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


def upsert_product_data(product_data: dict) -> None:
    """Upsert product data into the PostgreSQL database table."""
    connection = get_postgres_connection()
    if connection is None:
        raise ConnectionError("Failed to connect to the PostgreSQL database.")
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


if __name__ == "__main__":
    run_sql_scripts(settings.postgres_database, "queries/drop_products.sql")
    run_sql_scripts(settings.postgres_database, "queries/drop_embeddings.sql")

    run_sql_scripts(settings.postgres_database, "queries/create_products.sql")
    run_sql_scripts(settings.postgres_database, "queries/create_embeddings.sql")
