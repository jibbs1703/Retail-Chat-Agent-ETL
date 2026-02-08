"""Module for Asynchronous Ingestion of Product Data."""

import asyncio
from datetime import UTC, datetime

from config.settings import get_settings
from utilities.database import upsert_embedding_data, upsert_product_data
from utilities.embedding import create_image_from_url, embed_query
from utilities.logger import setup_logger
from utilities.product import (
    generate_product_caption,
    generate_product_id,
    generate_vector_id,
    stream_image_to_bytesio,
)
from utilities.s3 import upload_stream_to_s3
from utilities.scrape import scrape_stream
from utilities.vectorstore import create_point_with_metadata, upsert_points

logger = setup_logger("ingest.py")
settings = get_settings()

if __name__ == "__main__":
    import asyncio

    async def ingest_products():
        async for product in scrape_stream(
            categories=("jackets",),
            number_of_pages=1,
            limit_per_page=5
        ):
            product_id = generate_product_id(product["Product Title"].split("-")[0].strip())
            product_title = product["Product Title"].split("-")[0].strip()
            product_description = product.get("Product Details", [])
            product_caption = generate_product_caption(product_title, product_description)
            product_caption_embedding = embed_query(product_caption)
            product_data = {
                "product_id": product_id,
                "product_title": product_title,
                "description": product_description,
                "price": product.get("Product Price", ""),
                "num_images": product.get("No. of Images", 0),
                "product_images": product.get("Product Images", []),
                "product_caption": product_caption,
                "product_s3_image_urls": [],
                "financing": product.get("Financing", {}),
                "promo_tagline": product.get("Promo Tagline", ""),
                "sizes_available": product.get("Size Options", []),
                "product_url": product.get("Product URL", ""),
                "product_category": product.get("Product Category", ""),
                "product_inserted_at": datetime.now(UTC),
                "product_updated_at": datetime.now(UTC),
            }
            point = await create_point_with_metadata(
                embedding=product_caption_embedding,
                point_id=generate_vector_id(product_title, "text"),
                payload={
                    "product_id": product_id,
                    "num_images": product_data["num_images"],
                    "embedding_type": "text",
                }
            )
            await upsert_points(
                collection_name="jibbs_product_text_embeddings",
                points=[point]
            )
            upsert_product_data(
                product_data=product_data
            )

            for image_index, product_image_url in enumerate(product.get("Product Images", [])):
                product_bytesio = stream_image_to_bytesio(product_image_url)
                s3_image_url = upload_stream_to_s3(
                    bucket_name="jibbs-test-catalog",
                    data_stream=product_bytesio,
                    product_id=product_id,
                    image_index=image_index,
                )
                product_image_embedding = embed_query(create_image_from_url(product_image_url))
                product_vector_id = generate_vector_id(product_title, "image", image_index)
                product_image_embedding_data = {
                    "vector_id": product_vector_id,
                    "product_id": product_id,
                    "product_image_index": image_index,
                    "product_s3_image_url": s3_image_url,
                    "embedding_type": "image",
                    "embedding_inserted_at": datetime.now(UTC),
                    "embedding_updated_at": datetime.now(UTC),
                }
                point = await create_point_with_metadata(
                    embedding=product_image_embedding,
                    point_id=product_vector_id,
                    payload={
                        "product_id": product_image_embedding_data["product_id"],
                        "product_s3_image_url": (
                            product_image_embedding_data["product_s3_image_url"]
                        ),
                        "embedding_type": product_image_embedding_data["embedding_type"],
                    }
                )
                await upsert_points(
                    collection_name="jibbs_product_image_embeddings",
                    points=[point]
                )
                upsert_embedding_data(
                    embedding_data=product_image_embedding_data
                )

    asyncio.run(ingest_products())
