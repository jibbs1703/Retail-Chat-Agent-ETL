"""Simple Test DAG for Airflow Setup Verification."""

import asyncio
from datetime import datetime, timedelta

import requests
from airflow.sdk import dag, task

import queries
from config.settings import get_settings
from utilities.database import get_postgres_connection, run_sql_scripts
from utilities.logger import setup_logger
from utilities.s3 import get_s3_client
from utilities.scrape import ingest_products_async
from utilities.vectorstore import create_collection, get_qdrant_client

logger = setup_logger("products_dag.py")
settings = get_settings()


@dag(
    dag_id="products_dag",
    description="Product Ingestion DAG",
    schedule="0 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["Products", "ETL", "Ingestion"],
    dagrun_timeout=timedelta(hours=3),
    is_paused_upon_creation=False,
)
def products_etl():  # noqa: C901
    """Simple ETL DAG using TaskFlow API."""

    @task
    def relational_database_check() -> str:
        """Relational database check."""
        try:
            connection = get_postgres_connection()
            if connection is not None:
                logger.info("Successfully connected to PostgreSQL database.")
                connection.close()
                return "PostgreSQL Connection Successful"
            else:
                logger.error("Failed to connect to PostgreSQL database.")
                return "PostgreSQL Connection Failed"
        except requests.RequestException as e:
            logger.error("Error during PostgreSQL connection check: %s", e)
            return f"PostgreSQL Connection Check Error: {e}"

    @task
    def vector_database_check() -> str:
        """Vector database check."""
        try:
            qdrant_client = get_qdrant_client()
            if qdrant_client is not None:
                logger.info("Successfully connected to Qdrant vector database.")
                return "Qdrant Connection Successful"
            else:
                logger.error("Failed to connect to Qdrant vector database.")
                return "Qdrant Connection Failed"
        except requests.RequestException as e:
            logger.error("Error during Qdrant connection check: %s", e)
            return f"Qdrant Connection Check Error: {e}"

    @task
    def aws_s3_check() -> str:
        """AWS S3 Connection check."""
        try:
            s3_client = get_s3_client()
            if s3_client is not None:
                logger.info("Successfully connected to AWS S3.")
                return "AWS S3 Connection Successful"
            else:
                logger.error("Failed to connect to AWS S3.")
                return "AWS S3 Connection Failed"
        except requests.RequestException as e:
            logger.error("Error during AWS S3 connection check: %s", e)
            return f"AWS S3 Connection Check Error: {e}"

    @task
    def create_product_table():
        """Create the products table in the relational database if it doesn't exist."""
        run_sql_scripts(settings.postgres_database, queries, "create_products.sql")

    @task
    def create_embeddings_table():
        """Create the embeddings table in the relational database if it doesn't exist."""
        run_sql_scripts(settings.postgres_database, queries, "create_embeddings.sql")

    @task
    def create_qdrant_collections():
        """Create the Qdrant collections in the vector database if they don't exist."""
        asyncio.run(create_collection())

    @task(execution_timeout=timedelta(hours=2.5))
    def ingest_jackets():
        """Ingest jackets from scraper into vector and relational databases."""
        asyncio.run(ingest_products_async(category="jackets"))

    @task(execution_timeout=timedelta(hours=2.5))
    def ingest_shoes():
        """Ingest shoes from scraper into vector and relational databases."""
        asyncio.run(ingest_products_async(category="shoes"))

    check_database = relational_database_check()
    check_vectorstore = vector_database_check()
    check_aws_s3 = aws_s3_check()

    product_table = create_product_table()
    embedding_table = create_embeddings_table()
    qdrant_collections = create_qdrant_collections()

    jackets = ingest_jackets()
    shoes = ingest_shoes()

    product_table.set_upstream([check_database, check_vectorstore, check_aws_s3])
    embedding_table.set_upstream([check_database, check_vectorstore, check_aws_s3])
    qdrant_collections.set_upstream([check_database, check_vectorstore, check_aws_s3])
    jackets.set_upstream([product_table, embedding_table, qdrant_collections])
    shoes.set_upstream(jackets)


products_etl()
