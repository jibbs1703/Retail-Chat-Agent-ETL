"""AWS S3 Utility Module for Ingestion Pipeline."""

import logging
import os

import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_s3_client(
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name: str = os.getenv("AWS_REGION_NAME"),
):
    """
    Get S3 client.

    Args:
        aws_access_key_id (str): AWS access key ID.
        aws_secret_access_key (str): AWS secret access key.
        region_name (str): AWS region name.

    Returns:
        boto3.client: S3 client object.

        None: If credentials are not available or incomplete.
    """
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )
        logger.info("Successfully created S3 client.")
        return s3_client
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.error("Credentials are not available or incomplete: %s", e)
        return None
