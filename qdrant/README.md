# Standalone Qdrant Container Setup

This directory contains the Docker configuration for running a Qdrant vector database container.
This setup allows you to run Qdrant in a self-contained environment for vector similarity search
and storage.

## Prerequisites

- Docker installed on your system
- Sufficient disk space for vector data storage

## Building the Image

Navigate to the `qdrant` directory containing the Dockerfile and configuration files, then build the
Docker image:

```bash
cd qdrant
docker build -t qdrant-custom:latest .
```

## Running the Container

Run the container from the built image with the following command:

```bash
docker run -d \
  --name custom-qdrant-container \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_data:/qdrant/storage \
  qdrant-custom:latest
```

## API Usage

Once running, you can interact with Qdrant via HTTP API on `http://localhost:6333`.

- List collections
```bash
curl http://localhost:6333/collections
```

- Create a collection
```bash
curl -X PUT http://localhost:6333/collections/test_collection \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }'
```

## Web Dashboard

Qdrant provides a web-based dashboard for monitoring and managing your collections:

```
http://localhost:6333/dashboard
```

## Stopping the Container

```bash
docker stop custom-qdrant-container
```

## Removing the Container

```bash
docker rm custom-qdrant-container
```

## Persistent Storage

The container uses a Docker volume `qdrant_data` for persistent storage. Your vector data and collections will persist between container restarts.

To view volume data:
```bash
docker volume ls
docker volume inspect qdrant_data
```