-- Initialize TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- This file is run automatically on first postgres startup
-- The database and tables will be created by SQLAlchemy on first run

-- Convert audit_records to a TimescaleDB hypertable for fast time-series queries.
-- Runs after SQLAlchemy creates the table on first backend startup.
-- Using DO block so it doesn't fail if the table doesn't exist yet.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_records') THEN
        PERFORM create_hypertable('audit_records', 'timestamp', if_not_exists => TRUE, migrate_data => TRUE);
    END IF;
END
$$;
