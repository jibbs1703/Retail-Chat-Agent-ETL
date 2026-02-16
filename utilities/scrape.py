"""Streaming Web Scraper Module for FashionNova catalog."""

import asyncio
import re
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm

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
from utilities.vectorstore import create_point_with_metadata, upsert_points

logger = setup_logger("scrape.py")


class WebScraper:
    def __init__(
        self,
        request_delay: float,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
    ):
        self.request_delay = request_delay
        self.session = session
        self.semaphore = semaphore

    async def _fetch(self, url: str) -> str | None:
        """Internal helper to fetch content with rate limiting."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        async with self.semaphore:
            await asyncio.sleep(self.request_delay)
            try:
                async with self.session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    logger.warning("Non-200 status %s for %s", response.status, url)
                    return None
            except aiohttp.ClientError as e:
                logger.error("Error fetching %s: %s", url, e)
                return None

    def _parse_product_data(self, html: str, url: str) -> dict:
        """Parse a product page into a structured dict."""
        soup = BeautifulSoup(html, "html.parser")

        title = soup.title.string if soup.title else "No title found"
        price_node = soup.find("div", class_="text-red-600")
        price = price_node.get_text(strip=True) if price_node else "No price found"

        images = soup.select('div[data-testid^="product-image-"] picture img')
        img_urls = []
        for img in images:
            u = img.get("src") or (
                img.get("srcset", "").split(",")[0].strip().split(" ")[0]
                if img.get("srcset")
                else None
            )
            if u:
                img_urls.append(u.replace("&amp;", "&").split("?")[0])

        seen_imgs = set()
        unique_imgs = [u for u in img_urls if not (u in seen_imgs or seen_imgs.add(u))]

        details_container = soup.select_one('[data-testid="product-details-text"]')
        if details_container:
            li_items = details_container.select("li")
            product_details = (
                [li.get_text(strip=True) for li in li_items]
                if li_items
                else [
                    line
                    for line in details_container.get_text("\n", strip=True).split("\n")
                    if line
                ]
            )
        else:
            product_details = []

        financing = {}
        fin_btn = soup.select_one('button[data-testid="financing-options"]')
        if fin_btn:
            raw = fin_btn.get_text(" ", strip=True)
            m_payments = re.search(r"\bor\s+(\d+)\s+payments?\b", raw, flags=re.I)
            m_amount = re.search(r"(£\s?\d+(?:\.\d{2})?)", raw)
            financing = {
                "raw_text": raw,
                "payments_count": int(m_payments.group(1)) if m_payments else None,
                "payment_amount": m_amount.group(1).replace("£ ", "£") if m_amount else None,
            }

        size_options = []
        size_container = soup.select_one('[data-testid="product-size-options"]')
        if size_container:
            for btn in size_container.select('button[data-testid^="item-"]'):
                text = btn.get_text(" ", strip=True)
                if text:
                    size_options.append(text.split()[-1])

        return {
            "Product Title": title,
            "Product Price": price,
            "Product Images": unique_imgs,
            "No. of Images": len(unique_imgs),
            "Product Details": product_details,
            "Financing": financing,
            "Promo Tagline": (
                soup.select_one('[data-testid="product-tagline"]').get_text(" ", strip=True)
                if soup.select_one('[data-testid="product-tagline"]')
                else None
            ),
            "Size Options": list(dict.fromkeys(size_options)),
            "Product URL": url,
        }

    async def scrape_product(self, url: str) -> dict:
        """Fetch + parse a single product."""
        html = await self._fetch(url)
        if not html:
            return {"Product URL": url, "error": "Failed to retrieve page"}
        return self._parse_product_data(html, url)

    async def get_product_urls_from_collection(
        self, collection_url: str, limit: int = 60
    ) -> list[str]:
        """Extract product URLs from a collection page."""
        html = await self._fetch(collection_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        urls: list[str] = []
        for a in soup.select('a[href^="/products/"]'):
            href = a.get("href")
            if href:
                full = urljoin(collection_url, href)
                urls.append(urlparse(full)._replace(query="", fragment="").geturl())

        return list(dict.fromkeys(urls))[:limit]


async def scrape_stream(
    category: str,
    concurrent_requests: int = 10,
    number_of_pages: int = 3,
    limit_per_page: int = 60,
) -> AsyncGenerator[dict, None]:
    """
    Async generator that yields one product dict at a time.

    Each yielded item has the shape:
    {
        ...scraped fields...,
        "category": "<category_name>"
    }
    """
    sem = asyncio.Semaphore(concurrent_requests)

    async with aiohttp.ClientSession() as session:
        scraper = WebScraper(request_delay=1.0, session=session, semaphore=sem)

        collection_tasks: list[str] = []
        for page in range(1, number_of_pages + 1):
            url = f"https://www.fashionnova.com/collections/{category}?division=women&page={page}"
            collection_tasks.append(url)

        logger.info("Gathering product URLs from %d collection pages...", len(collection_tasks))

        urls = []
        for url in collection_tasks:
            page_urls = await scraper.get_product_urls_from_collection(url, limit=limit_per_page)
            urls.extend(page_urls)

        urls = list(dict.fromkeys(urls))

        total_urls = len(urls)
        logger.info("Scraping %d products from category: %s", total_urls, category)

        if not urls:
            logger.info("No products found for category: %s", category)
            return

        tasks = [scraper.scrape_product(url) for url in urls]

        for coro in tqdm.as_completed(tasks, total=len(tasks), desc=f"Scraping {category.title()}"):
            product = await coro
            product["Product Category"] = category
            yield product


async def ingest_products_async(
    category: str,
):
    async for product in scrape_stream(category=category, number_of_pages=5, limit_per_page=5):
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
            },
        )
        await upsert_points(collection_name="jibbs_product_text_embeddings", points=[point])
        upsert_product_data(product_data=product_data)

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
                    "product_s3_image_url": (product_image_embedding_data["product_s3_image_url"]),
                    "embedding_type": product_image_embedding_data["embedding_type"],
                },
            )
            await upsert_points(collection_name="jibbs_product_image_embeddings", points=[point])
            upsert_embedding_data(embedding_data=product_image_embedding_data)
