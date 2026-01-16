# Standalone PostgreSQL Container Setup

This directory contains the Docker configuration for running a PostgreSQL relational database container.
This setup allows you to run PostgreSQL in a self-contained environment for storing product catalog data,
user information, and other relational data from the web scraping pipeline.

## Prerequisites

- Docker installed on your system
- Sufficient disk space for database persistence

## Building the Image

Navigate to the `database` directory containing the Dockerfile, then build the Docker image:

```bash
cd database
docker build -t postgres-custom:latest .
```

## Running the Container

Run the container from the built image with the following command:

```bash
docker run -d \
  --name retail-postgres \
  -p 5432:5432 \
  -v database_data:/var/lib/postgresql/data \
  -e POSTGRES_USER=retailadmin \
  -e POSTGRES_PASSWORD=retailpass123 \
  -e POSTGRES_DB=retail_catalog \
  postgres-custom:latest
```

## Using PostgreSQL CLI

Connect to PostgreSQL using psql:

```bash
psql -h localhost -U retailadmin -d retail_catalog
```

## Database Credentials

- **User:** `retailadmin`
- **Password:** `retailpass123`
- **Database:** `retail_catalog`
- **Port:** `5432`

## Data Persistence

This container uses PostgreSQL's built-in persistence. Data is automatically saved to disk in the mounted volume.

- Check database size:
```bash
psql -h localhost -U retailadmin -d retail_catalog -c "SELECT pg_size_pretty(pg_database_size('retail_catalog'));"
```

- List all tables:
```bash
psql -h localhost -U retailadmin -d retail_catalog -c "\dt"
```

## Docker Compose Integration

This PostgreSQL container is integrated with Docker Compose. Start it along with other services:

```bash
docker-compose up -d postgres
```

Check the health status:
```bash
docker-compose ps
```

## Backup and Restore

Backup the database:
```bash
pg_dump -h localhost -U retailadmin retail_catalog > backup.sql
```

Restore from backup:
```bash
psql -h localhost -U retailadmin retail_catalog < backup.sql
```
