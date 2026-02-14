#!/bin/bash

docker run \
-it \
--name jibbs-embedding-container \
-p 6333:6333 \
-v qdrant_data:/qdrant/storage \
-d qdrant/qdrant:latest