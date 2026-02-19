"""AWS S3 Utility Module for Ingestion Pipeline."""

import logging
from io import BytesIO

import boto3
from botocore.exceptions import (
    ClientError,
    DataNotFoundError,
    NoCredentialsError,
    PartialCredentialsError,
)
from dotenv import load_dotenv

from config.settings import get_settings

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("s3.py")
settings = get_settings()


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
    Create an S3 bucket if it does not already exist.

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
        return True
    try:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": settings.aws_region},
        )
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
