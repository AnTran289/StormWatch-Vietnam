/*
Create the initial PosrtgreSQL database schema and tables for the application.

Define:
1. Reference location data
2. Raw hourly weather data
3. Pipeline execution metadata
*/

-- ============================================================
-- Create application schemas
-- ============================================================

-- raw contains data as it is ingested from the source, without any transformations applied
CREATE SCHEMA IF NOT EXISTS raw;

-- analytiucs contains data that has been transformed and is ready for analysis
CREATE SCHEMA IF NOT EXISTS analytics;

-- metadata contains information about the execution of the data pipeline
CREATE SCHEMA IF NOT EXISTS metadata;

-- ============================================================
-- Location dimension
-- ============================================================

-- create new table
CREATE TABLE IF NOT EXISTS analytics.dim_location (
    location_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    province_code VARCHAR(20) NOT NULL,
    province_name VARCHAR(150) NOT NULL,
    province_name_en VARCHAR(150),
    administrative_unit VARCHAR(150),
    administrative_region VARCHAR(150),
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Basic coordinate constraints for approximate area
    CONSTRAINT check_latitude CHECK (latitude BETWEEN 8 AND 24),
    CONSTRAINT check_longitude CHECK (longitude BETWEEN 102 AND 110)
);

-- Compatibility view for older code that still references the pluralized name.
CREATE OR REPLACE VIEW analytics.dim_locations AS
SELECT *
FROM analytics.dim_location;

-- ============================================================
-- Raw hourly weather table
-- ============================================================

CREATE TABLE IF NOT EXISTS raw.weather_hourly (

    -- Large identifier for fact table
    weather_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Foreign key connecting weather data to the location dimension
    location_id INTEGER NOT NULL REFERENCES analytics.dim_location(location_id),

    -- Time when Open-Meteo made the forecast
    forecast_time TIMESTAMPTZ NOT NULL,

    -- Timestamp for pipeline forecast collection
    ingested_at TIMESTAMPTZ NOT NULL,
    temperature_c NUMERIC(6,2),
    relative_humidity_percent NUMERIC(6,2),
    precipitation_mm NUMERIC(10,2),
    rain_mm NUMERIC(10,2),
    wind_speed_kmh NUMERIC(8,2),
    wind_gusts_kmh NUMERIC(8,2),
    surface_pressure_hpa NUMERIC(8,2),
    weather_code INTEGER,

    -- Store name of API
    source_name VARCHAR(50) NOT NULL DEFAULT 'open_meteo',

    -- Prevent the same location and forecast time from being ingested multiple times
    CONSTRAINT unique_weather_forecast UNIQUE (location_id, forecast_time, ingested_at),

    CONSTRAINT check_precipitation_non_negative CHECK (precipitation_mm >= 0 or precipitation_mm IS NULL),

    CONSTRAINT check_rain_non_negative CHECK (rain_mm >= 0 or rain_mm IS NULL)
);

-- ============================================================
-- Pipeline run metadata
-- ============================================================

CREATE TABLE IF NOT EXISTS metadata.pipeline_runs (

   -- Unique ID for each execution of the data pipeline
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    pipeline_name VARCHAR(100) NOT NULL,

    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    completed_at TIMESTAMPTZ,

    -- Status of the pipeline run (e.g., 'success', 'failure', 'running')
    status VARCHAR(20) NOT NULL,

    -- Number of records
    rows_extracted INTEGER default 0,
    rows_loaded INTEGER default 0,

    -- Store error messages or logs if the pipeline fails
    error_message TEXT,
    CONSTRAINT check_status CHECK (status IN ('success', 'failed', 'running'))
);

-- ============================================================
-- Indexes
-- ============================================================

-- Speeds up queries that filter or sort by columns
CREATE INDEX IF NOT EXISTS idx_weather_hourly_location_time ON raw.weather_hourly (location_id, forecast_time);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON metadata.pipeline_runs (started_at);
