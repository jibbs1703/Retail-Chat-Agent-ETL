"""Simple Test DAG for Airflow Setup Verification."""

from datetime import datetime

import requests
from airflow.sdk import dag, task

from utilities.database import get_postgres_connection
from utilities.logger import setup_logger
from utilities.s3 import get_s3_client
from utilities.vectorstore import get_qdrant_client

logger = setup_logger("jackets_dag.py")


@dag(
    dag_id="jackets_products_dag",
    description="Jackets Product Ingestion DAG",
    schedule="0 * * * *",  # Runs every hour
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["Jackets", "ETL","Products"],
)
def jackets_products_etl():
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
    
    relational_database_check()
    vector_database_check()
    aws_s3_check()


jackets_products_etl()
