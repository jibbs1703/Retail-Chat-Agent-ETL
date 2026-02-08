"""Embedding Utilities Module for Ingestion Pipeline."""

from io import BytesIO

import numpy as np
import requests
import torch
from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor, CLIPModel, CLIPProcessor

from ingestion.config.settings import get_device, get_settings
from ingestion.utilities.logger import setup_logger

device = get_device()
logger = setup_logger()
settings = get_settings()

_blip_model: BlipForConditionalGeneration | None = None
_clip_model: CLIPModel | None = None
_clip_processor: CLIPProcessor | None = None
_blip_processor: BlipProcessor | None = None


def load_blip_model() -> BlipForConditionalGeneration:
    """
    Load BLIP model from pretrained checkpoint.

    Returns:
        BlipForConditionalGeneration: Loaded BLIP model on appropriate device.
    """
    global _blip_model
    if _blip_model is None:
        device = get_device()
        _blip_model = BlipForConditionalGeneration.from_pretrained(settings.blip_model_name).to(
            device
        )
    return _blip_model


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


def load_blip_processor():
    """
    Load BLIP processor from pretrained checkpoint.

    Returns:
        BlipProcessor: Loaded BLIP processor.
    """
    global _blip_processor
    if _blip_processor is None:
        _blip_processor = BlipProcessor.from_pretrained(settings.blip_model_name)
    return _blip_processor


def generate_image_caption(
    image: Image.Image | BytesIO | str,
    max_length: int = 50) -> str:
    """
    Generate a caption for an image using BLIP model.

    Args:
        image (Image.Image | BytesIO | str): PIL Image, BytesIO stream, or image
                                             URL to generate caption for.
        product_title (str): Title of the product to include in the caption.
        max_length (int): Maximum length of generated caption. Defaults to 50.

    Returns:
        str: Generated caption text.

    Raises:
        ValueError: If image is not a PIL Image, BytesIO object, or valid URL string.
    """
    if isinstance(image, BytesIO):
        image.seek(0)
        image = Image.open(image).convert("RGB")
    elif isinstance(image, str):
        try:
            response = requests.get(image, timeout=10)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGB")
        except Exception as e:
            logger.error("Error fetching image from URL %s: %s", image, e)
            raise ValueError(f"Could not fetch image from URL: {image}") from e
    elif not isinstance(image, Image.Image):
        raise ValueError("Input must be a PIL Image, BytesIO object, or a valid image URL string")
    
    device = get_device()
    blip_model = load_blip_model()
    blip_processor = load_blip_processor()
    
    try:
        inputs = blip_processor(images=image,
                                return_tensors="pt").to(device)
        with torch.no_grad():
            out = blip_model.generate(**inputs, max_length=max_length)
        caption = blip_processor.decode(out[0], skip_special_tokens=True)
        return caption.strip()
    except Exception as e:
        logger.error("Error generating caption: %s", e)
        raise


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

    if hasattr(emb, "norm"):
        emb = emb / emb.norm(dim=-1, keepdim=True)
    else:
        logger.warning("Model output does not have 'norm' attribute. Normalization skipped.")

    return emb.cpu().numpy()[0].astype("float32")


if __name__ == "__main__":
    # Example usage
    from PIL import Image

    test_image = Image.new("RGB", (224, 224), color="red")
    caption = generate_image_caption(test_image)
    print(f"Caption: {caption}")

    text_embedding = embed_query("A red square")
    print(f"Text Embedding Shape: {text_embedding.shape}")

    image_embedding = embed_query(test_image)
    print(f"Image Embedding Shape: {image_embedding.shape}")
