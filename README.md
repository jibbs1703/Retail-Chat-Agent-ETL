# Product Ingestion Pipeline

This directory contains the Airflow DAGs and ingestion logic for scraping products from e-commerce websites and loading them into PostgreSQL and Qdrant.

## Overview

The ingestion pipeline performs the following steps:

1. **Scraping**: Extracts product URLs from collection pages
2. **Product Parsing**: Parses product data (title, price, images, description, etc.) from product pages
3. **Image Upload**: Uploads product images to S3
4. **PostgreSQL Upsert**: Stores product metadata in PostgreSQL
5. **Embedding Generation**: Creates text and image embeddings using CLIP
6. **Qdrant Upsert**: Stores embeddings in Qdrant vector database
7. **Tracking**: Records embedding metadata in PostgreSQL

## Files

- `ingest.py`: Core ingestion logic with scraping, parsing, and database operations
- `dags/product_ingestion_dag.py`: Airflow DAG that orchestrates the ingestion pipeline
- `dags/database_health_check_dag.py`: DAG to verify database connectivity
- `dags/sample_dag.py`: Example DAG for testing

## Setup

### 1. Environment Variables

Ensure the following environment variables are set in your `.env` file:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_S3_BUCKET_NAME=your_bucket_name
AWS_REGION=us-east-1

# Database Configuration
POSTGRES_HOST=relational-db
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=your_database
POSTGRES_PORT=5432

# Qdrant Configuration
QDRANT_URL=http://vector-db:6333

# Model Configuration
CLIP_MODEL_NAME=openai/clip-vit-base-patch32

# Ingestion Configuration (optional)
INGESTION_SCHEDULE=0 2 * * *  # Daily at 2 AM
PRODUCT_CATEGORIES=shoes,bodysuits,jackets
PRODUCT_CONCURRENT_REQUESTS=5
PRODUCT_REQUEST_DELAY=1.0
```

### 2. Dependencies

The ingestion pipeline requires several Python packages. These are automatically installed via `_PIP_ADDITIONAL_REQUIREMENTS` in the docker-compose file, or you can install them manually:

```bash
pip install -r ingestion/requirements.txt
```

**Note**: Installing `torch` and `transformers` can take several minutes as they are large packages.

### 3. Database Schema

Ensure your PostgreSQL database has the required tables. The schema is defined in `postgres/init.sql` and includes:

- `products`: Product metadata
- `product_images`: Product image URLs and S3 keys
- `embeddings`: Tracking table for Qdrant embeddings

## Usage

### Running the DAG

1. **Start Airflow services**:
   ```bash
   docker-compose -f ingestion-docker-compose.yaml up -d
   ```

2. **Access Airflow UI**: Navigate to `http://localhost:8080`

3. **Enable the DAG**: Find `product_ingestion` in the DAG list and toggle it on

4. **Trigger manually** (optional): Click the play button to run immediately

### Configuration

The DAG can be configured via environment variables:

- `INGESTION_SCHEDULE`: Cron expression for automatic runs (default: `0 2 * * *`)
- `PRODUCT_CATEGORIES`: Comma-separated list of categories to scrape
- `PRODUCT_CONCURRENT_REQUESTS`: Number of concurrent HTTP requests (default: 5)
- `PRODUCT_REQUEST_DELAY`: Delay between requests in seconds (default: 1.0)

### Customizing Parsing Logic

The parsing logic in `ingest.py` uses multiple extraction methods:

1. **JSON-LD structured data** (most reliable)
2. **Open Graph meta tags**
3. **Common HTML patterns** (CSS selectors)
4. **Fallback methods**

To customize for a specific website, modify the `_parse_product_data()` and `get_product_urls_from_collection()` methods in `ingest.py`.

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

## Error Handling

The pipeline includes error handling at multiple levels:

- **Network errors**: Retries with exponential backoff
- **Parsing errors**: Logs and continues with next product
- **Database errors**: Rollback and log
- **S3 errors**: Logs and continues (failed images won't block product)

## Monitoring

- Check Airflow logs for detailed execution logs
- Monitor PostgreSQL for product counts
- Check Qdrant collections for embedding counts
- Review S3 bucket for uploaded images

## Troubleshooting

### DAG not appearing
- Check that `product_ingestion_dag.py` is in the `dags/` directory
- Verify Airflow can import the module (check logs)
- Ensure all dependencies are installed

### Import errors
- Verify `backend` directory is mounted in docker-compose
- Check that all Python packages are installed
- Review Airflow worker logs for import errors

### Parsing issues
- Test parsing logic on sample HTML
- Adjust CSS selectors for your target website
- Enable debug logging to see parsed data

### Performance issues
- Reduce `PRODUCT_CONCURRENT_REQUESTS` if hitting rate limits
- Increase `PRODUCT_REQUEST_DELAY` to be more respectful
- Consider pagination for large collections

## Development

To test the ingestion logic locally:

```python
from ingest import run_ingestion

run_ingestion(
    bucket_name="your-bucket",
    concurrent_requests=3,
    categories=("shoes",),
    request_delay=1.0
)
```

## Notes

- The parsing logic is designed to be generic and work with multiple e-commerce sites
- For production use, consider adding:
  - Rate limiting
  - Proxy rotation
  - User-agent rotation
  - Retry logic with exponential backoff
  - Monitoring and alerting
  - Data validation
