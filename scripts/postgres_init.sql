-- PostgreSQL initialization script
-- Run once on first container startup

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- For text search on queries

-- Ensure timezone is UTC
SET timezone = 'UTC';

-- Create a read-only user for analytics/monitoring
-- DO NOT use this for application connections
-- CREATE USER rag_readonly WITH PASSWORD 'CHANGE_THIS';
-- GRANT CONNECT ON DATABASE rag_saas TO rag_readonly;
-- GRANT USAGE ON SCHEMA public TO rag_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO rag_readonly;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO rag_readonly;
