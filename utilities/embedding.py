"""Embedding Utilities Module for Ingestion Pipeline."""

from io import BytesIO

import numpy as np
import requests
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from config.settings import get_device, get_settings
from utilities.logger import setup_logger

device = get_device()
logger = setup_logger("embedding.py")
settings = get_settings()

_clip_model: CLIPModel | None = None
_clip_processor: CLIPProcessor | None = None


def load_clip_model() -> CLIPModel:
    """
    Load CLIP model from pretrained checkpoint.

    Returns:
        CLIPModel: Loaded CLIP model on appropriate device.
    """
    global _clip_model
    if _clip_model is None:
        device = get_device()
        _clip_model = CLIPModel.from_pretrained(settings.clip_model_name).to(device)
    return _clip_model


def load_clip_processor() -> CLIPProcessor:
    """
    Load CLIP processor from pretrained checkpoint.

    Returns:
        CLIPProcessor: Loaded CLIP processor.
    """
    global _clip_processor
    if _clip_processor is None:
        _clip_processor = CLIPProcessor.from_pretrained(settings.clip_model_name)
    return _clip_processor


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


def embed_query(query: str | Image.Image) -> np.ndarray:
    """
    Embed either text or image query using CLIP model.

    Args:
        query (str | Image.Image): Text or image query to embed.

    Returns:
        np.ndarray: Normalized embedding vector.

    Raises:
        ValueError: If query is neither string nor image.
    """
    device = get_device()
    clip_model = load_clip_model()
    clip_processor = load_clip_processor()

    if isinstance(query, Image.Image):
        inputs = clip_processor(images=query, return_tensors="pt").to(device)
        with torch.no_grad():
            emb = clip_model.get_image_features(**inputs)
    elif isinstance(query, str):
        inputs = clip_processor(
            text=[query], return_tensors="pt", padding=True, truncation=True, max_length=77
        ).to(device)
        with torch.no_grad():
            emb = clip_model.get_text_features(**inputs)
    else:
        raise ValueError("Query must be either a string or an image")

    if hasattr(emb, "pooler_output"):
        emb = emb.pooler_output
    
    if hasattr(emb, "norm"):
        emb = emb / emb.norm(dim=-1, keepdim=True)
    
    else:
        logger.warning("Model output does not have 'norm' attribute. Normalization skipped.")

    if isinstance(emb, torch.Tensor):
        return emb.cpu().numpy().flatten().astype("float32")
    else:
        return np.array(emb).flatten().astype("float32")