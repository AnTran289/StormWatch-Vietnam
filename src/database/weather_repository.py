"""
Provide PostgreSQL operations:
1. Read active monitoring locations.
2. Insert hourly weather forecasts
3. Record pipeline execution status (running, success, failed)

--> Separate database operations from the main ETL logic for easier testing and maintenance.
"""

# datetime is used in type annotations and database records.
from datetime import datetime

# Any allows dictionaries containing different value types.
from typing import Any

# pandas is used to read SQL query results into a DataFrame.
import pandas as pd

# text creates parameterised SQL statements.
from sqlalchemy import text

# Import the shared SQLAlchemy engine.
from src.database.connection import get_engine


def get_locations() -> pd.DataFrame:
    """
    Read all monitoring locations from PostgreSQL.
    """

    query = text(
        """
        SELECT
            location_id,
            province_code,
            province_name,
            latitude,
            longitude
        FROM analytics.dim_locations
        ORDER BY province_code
        """
    )

    engine = get_engine()

    # read_sql() executes the SQL and returns a DataFrame.
    with engine.connect() as connection:
        locations_df = pd.read_sql(
            query,
            connection,
        )

    return locations_df


def start_pipeline_run(
    pipeline_name: str,
) -> int:
    """
    Record the start of a pipeline execution.
    """
    query = text(
        """
        INSERT INTO metadata.pipeline_runs (
            pipeline_name,
            status
        )
        VALUES (
            :pipeline_name,
            'running'
        )
        RETURNING run_id
        """
    )

    engine = get_engine()

    # Use a transaction to ensure the run_id is returned correctly.
    with engine.begin() as connection:
        run_id = connection.execute(
            query,
            {"pipeline_name": pipeline_name},
        ).scalar_one()

    return run_id


def complete_pipeline_run(
    run_id: int,
    rows_extracted: int,
    rows_loaded: int,
) -> None:
    """
    Mark a pipeline execution as successful.
    """

    query = text(
        """
        UPDATE metadata.pipeline_runs
        SET
            completed_at = CURRENT_TIMESTAMP,
            status = 'success',
            rows_extracted = :rows_extracted,
            rows_loaded = :rows_loaded,
            error_message = NULL
        WHERE run_id = :run_id
        """
    )

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "run_id": run_id,
                "rows_extracted": rows_extracted,
                "rows_loaded": rows_loaded,
            },
        )


def fail_pipeline_run(
    run_id: int,
    error_message: str,
    rows_extracted: int = 0,
    rows_loaded: int = 0,
) -> None:
    """
    Mark a pipeline execution as failed.
    """

    query = text(
        """
        UPDATE metadata.pipeline_runs
        SET
            completed_at = CURRENT_TIMESTAMP,
            status = 'failed',
            rows_extracted = :rows_extracted,
            rows_loaded = :rows_loaded,
            error_message = :error_message
        WHERE run_id = :run_id
        """
    )

    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "run_id": run_id,
                "rows_extracted": rows_extracted,
                "rows_loaded": rows_loaded,

                # Limit the error message length to avoid exceeding database column size.
                "error_message": error_message[:2000],
            },
        )


def upsert_weather_records(
    records: list[dict[str, Any]],
) -> int:
    """
    Insert weather rows while safely ignoring exact duplicates.
    """

    if not records:
        return 0

    query = text(
        """
        INSERT INTO raw.weather_hourly (
            location_id,
            forecast_time,
            ingested_at,
            temperature_c,
            relative_humidity_percent,
            precipitation_mm,
            rain_mm,
            wind_speed_kmh,
            wind_gusts_kmh,
            surface_pressure_hpa,
            weather_code,
            source_name
        )
        VALUES (
            :location_id,
            :forecast_time,
            :ingested_at,
            :temperature_c,
            :relative_humidity_percent,
            :precipitation_mm,
            :rain_mm,
            :wind_speed_kmh,
            :wind_gusts_kmh,
            :surface_pressure_hpa,
            :weather_code,
            'open_meteo'
        )
        ON CONFLICT (
            location_id,
            forecast_time,
            ingested_at
        )
        DO NOTHING
        """
    )

    engine = get_engine()

    # Pass a list of dictionaries to execute many inserts in one transaction.
    with engine.begin() as connection:
        connection.execute(
            query,
            records,
        )

    return len(records)