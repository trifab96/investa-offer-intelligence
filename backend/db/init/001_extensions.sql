-- Database initialization: enable extensions used by the app.
-- Runs automatically on first container start (docker-entrypoint-initdb.d).

CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- trigram fuzzy address matching
CREATE EXTENSION IF NOT EXISTS postgis;   -- optional geo distance (image: postgis)
