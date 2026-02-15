# Retail Chat Agent - Product Ingestion Pipeline

A production-grade ETL pipeline that scrapes e-commerce product catalogs, enriches them with AI-generated embeddings, and stores them in vector and relational databases to power semantic search for a retail chat agent.

## Purpose

This pipeline automates the ingestion and vectorization of product catalogs, enabling the retail chat agent to perform intelligent semantic search across millions of products. It combines web scraping, image processing, and multi-modal embeddings to create a searchable product knowledge base.

## Tech Stack

- **Orchestration**: Apache Airflow
- **Data Storage**: PostgreSQL (relational), Qdrant (vector)
- **Embeddings**: OpenAI CLIP (text + image)
- **Object Storage**: AWS S3
- **Language**: Python 3.11
- **Containerization**: Docker

## How It Works

The ingestion pipeline performs the following steps:

1. **Scraping**: Extracts product URLs from collection pages
2. **Product Parsing**: Parses product data (title, price, images, description, etc.) from product pages
3. **Image Upload**: Uploads product images to S3
4. **PostgreSQL Upsert**: Stores product metadata in PostgreSQL
5. **Embedding Generation**: Creates text and image embeddings using CLIP
6. **Qdrant Upsert**: Stores embeddings in Qdrant vector database
7. **Tracking**: Records embedding metadata in PostgreSQL

## Architecture


```
┌─────────────────┐
│  Collection URL │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Extract URLs   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Parse Products  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────┐
│   S3   │ │PostgreSQL│
└────────┘ └────┬─────┘
                │
                ▼
         ┌──────────────┐
         │ Generate     │
         │ Embeddings   │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │    Qdrant    │
         └──────────────┘
```

### Setup Instructions

1. For instructions on setting up the databases, see [docs/how-to/create-databases.md](docs/how-to/create-databases.md)

2. Create an AWS S3 bucket and configure credentials in `config/settings.py`

3. Use the env.example file to create a `.env` file with necessary environment variables (database URLs, S3 credentials, etc.)

4. Build the custom Airflow image with dependencies and DAGs baked in:
   ```bash
   make ingestion-build
   ```

5. Start the Airflow stack with Docker Compose:
   ```bash
   make ingestion-up
   ```

## Disclaimer

This project is for **informative and educational purposes only**. It is not intended for commercial use. The code, documentation, and examples provided are meant to demonstrate concepts and practices related to ETL pipelines, vector databases, and semantic search. Users are responsible for complying with applicable laws and terms of service when using or adapting this code.
