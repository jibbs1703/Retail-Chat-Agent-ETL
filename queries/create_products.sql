CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_title VARCHAR(255),
    description TEXT[],
    price VARCHAR(50),
    num_images INTEGER,
    product_images TEXT[],
    product_images_captions TEXT[],
    s3_image_urls TEXT[],
    financing JSONB,
    promo_tagline TEXT,
    sizes_available TEXT[],
    product_url TEXT,
    product_category VARCHAR(100),
    product_inserted_at TIMESTAMPTZ,
    product_updated_at TIMESTAMPTZ
);