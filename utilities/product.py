"""Product Utilities Module for Ingestion Pipeline."""

import hashlib
from io import BytesIO

import requests


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


def generate_product_id(product_title: str) -> str:
    """Generate a product ID based on product title."""
    content = f"{product_title}"
    return int(hashlib.sha256(content.encode()).hexdigest(), 16) % (2**63)


def generate_vector_id(product_title: str, embedding_type: str, index: int | None = None) -> str:
    """Generate a vector ID based on product title."""
    content = f"{product_title}_{embedding_type}_{index}"
    return int(hashlib.sha256(content.encode()).hexdigest(), 16) % (2**63)


def generate_product_caption(
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
