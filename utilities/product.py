"""Product Utilities Module for Ingestion Pipeline."""

import hashlib

import requests
import torch
from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor

from ingestion.config.settings import get_device, get_settings

settings = get_settings()
device = get_device()
PROMPT = (
    "describe only the retail product image in detail, "
    "highlighting its features, colors, style, and materials."
)


def generate_product_id(product_title: str) -> str:
    """Generate a product ID based on product title."""
    content = f"{product_title}"
    return int(hashlib.sha256(content.encode()).hexdigest(), 16) % (2**63)


def generate_vector_id(product_title: str, embedding_type: str, index: int = 0) -> str:
    """Generate a vector ID based on product title."""
    content = f"{product_title}_{embedding_type}_{index}"
    return int(hashlib.sha256(content.encode()).hexdigest(), 16) % (2**63)


def generate_product_caption(image_url: str, prompt: str = None) -> str:
    """
    Generates a detailed caption for a retail product image using BLIP Large model.

    Args:
        image_url (str): URL of the product image.
        prompt (str, optional): Optional text prompt to guide captioning.

    Returns:
        str: Generated caption (excluding the prompt text).
    """
    try:
        model_name = settings.blip_model_name

        processor = BlipProcessor.from_pretrained(model_name)
        model = BlipForConditionalGeneration.from_pretrained(model_name).to(device)

        image = Image.open(requests.get(image_url, stream=True, timeout=10.0).raw).convert("RGB")

        if prompt:
            inputs = processor(image, prompt, return_tensors="pt").to(device)
        else:
            inputs = processor(image, return_tensors="pt").to(device)

        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_length=150,
                min_length=50,
                num_beams=4,
                temperature=0.0,
                do_sample=False,
            )
        caption = processor.decode(output_ids[0], skip_special_tokens=True)

        if prompt and caption.lower().startswith(prompt.lower()):
            caption = caption[len(prompt) :].strip()

        return caption

    except requests.RequestException as e:
        return f"Error: {e}"


if __name__ == "__main__":
    product_image_url = "https://cdn.shopify.com/s/files/1/0293/9277/files/09-24-24_S7_34_ZDF01S430031_MultiColor_CZ_DJ_11-24-49_PLUS_10726_EH.jpg"
    caption = generate_product_caption(image_url=product_image_url, prompt=PROMPT)
    print("Generated Product Caption:", caption)
