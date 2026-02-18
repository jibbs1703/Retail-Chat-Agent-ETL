"""Retail Product Agent Product Data Ingestion Configurations Module."""

import os
from functools import lru_cache

import torch
from dotenv import load_dotenv
from pydantic_settings import BaseSettings


def get_device() -> torch.device:
    """Get the appropriate device for model inference."""
    return (
        torch.device("cuda")
        if torch.cuda.is_available()
        else torch.device("mps")
        if torch.backends.mps.is_available()
        else torch.device("cpu")
    )


class IngestionSettings(BaseSettings):
    """
    Application settings for the Retail Product Agent Product Data Ingestion.

    Settings can be loaded from environment variables or .env file.

    """

    load_dotenv()
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID")
    aws_region: str = os.getenv("AWS_REGION")
    aws_s3_bucket_name: str = os.getenv("AWS_S3_BUCKET_NAME")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY")
    postgres_database: str = os.getenv("POSTGRES_DATABASE")
    postgres_host: str = os.getenv("POSTGRES_HOST")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD")
    postgres_port: int = int(os.getenv("POSTGRES_PORT"))
    postgres_user: str = os.getenv("POSTGRES_USER")
    qdrant_url: str = os.getenv("QDRANT_URL")
    qdrant_collections: str = os.getenv("QDRANT_COLLECTIONS")


@lru_cache
def get_settings() -> IngestionSettings:
    """Get or create a cached IngestionSettings instance.

    Returns:
        IngestionSettings: Cached ingestion settings instance.
    """
    return IngestionSettings()


if __name__ == "__main__":
    settings = get_settings()
    print(settings.qdrant_collections)
