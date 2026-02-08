CREATE USER retailadmin WITH PASSWORD 'retailpass123';

CREATE DATABASE "jibbs-product-catalog" OWNER retailadmin;

\connect "jibbs-product-catalog";

ALTER SCHEMA public OWNER TO retailadmin;

GRANT ALL PRIVILEGES ON SCHEMA public TO retailadmin;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON TABLES TO retailadmin;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON SEQUENCES TO retailadmin;
