CREATE TABLE IF NOT EXISTS embeddings (
    vector_id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) REFERENCES products (product_id),
    product_image_index INT,
    product_s3_image_url VARCHAR(255),
    embedding_type VARCHAR(50),
    embedding_inserted_at TIMESTAMPTZ,
    embedding_updated_at TIMESTAMPTZ
);
