"""Retail Product Agent Backend Core Configurations Module."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


class ApplicationSettings(BaseSettings):
    """
    Application settings for the Give-It-A-Summary backend.

    Settings can be loaded from environment variables or .env file.

    """

    load_dotenv()
    application_api_prefix: str = "/api/v1"
    application_debug_flag: bool = False
    application_description: str = "AI powered multimodal product search backend."
    application_device: str = "cpu"
    application_name: str = "Retail Product Agent Backend"
    application_version: str = "1.0.0"
    aws_access_key_id :str = os.getenv("aws_access_key_id")
    aws_region: str = os.getenv("aws_region")
    aws_s3_bucket_name: str = os.getenv("aws_s3_bucket_name")
    aws_secret_access_key: str = os.getenv("aws_secret_access_key")
    blip_model_name: str = os.getenv("blip_model_name")
    clip_model_name: str = os.getenv("clip_model_name")
    max_image_size: int = 4096
    postgres_database: str = os.getenv("postgres_database")
    postgres_host: str = os.getenv("postgres_host")
    postgres_password: str = os.getenv("postgres_password")
    postgres_port: int = int(os.getenv("postgres_port"))
    postgres_user: str = os.getenv("postgres_user")
    qdrant_collections: list[str] = os.getenv("qdrant_collections").split(",")
    qdrant_url: str = os.getenv("qdrant_url")
    redis_url: str = os.getenv("redis_url")
    rerank_model_name: str = os.getenv("rerank_model_name")
    supported_image_extensions: set[str] = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    supported_image_formats: set[str] = {"JPEG", "PNG", "GIF", "WEBP", "BMP"}


@lru_cache
def get_settings() -> ApplicationSettings:
    """Get or create a cached ApplicationSettings instance.

    Returns:
        ApplicationSettings: Cached application settings instance.
    """
    return ApplicationSettings()
