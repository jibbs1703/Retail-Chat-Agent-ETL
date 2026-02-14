#!/bin/bash

docker run \
-it \
--name jibbs-catalog-container \
-e POSTGRES_DB=jibbs-product-catalog \
-e POSTGRES_PASSWORD=retailpass123 \
-e POSTGRES_USER=retailadmin \
-p 5432:5432 \
-v pgdata:/var/lib/postgresql \
-d postgres:latest


docker exec -it jibbs-catalog-container psql -U postgres -c "\du"

CREATE USER retailadmin WITH PASSWORD 'retailpass123';
GRANT ALL PRIVILEGES ON DATABASE "jibbs-product-catalog" TO retailadmin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO retailadmin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO retailadmin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT ALL ON TABLES TO retailadmin;
