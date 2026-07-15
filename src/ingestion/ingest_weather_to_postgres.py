"""
Run the complete Open-Meteo weather ingestion pipeline.

Pipeline:
1. Read 34 locations from PostgreSQL
2. Call Open-Meteo for every location
3. Save raw JSON responses
4. Transform hourly JSON into records
5. Insert records into raw.weather_hourly
6. Record pipeline success or failure
"""


import json

import logging


from datetime import datetime, timezone


from pathlib import Path


from typing import Any


import pandas as pd


from src.clients.open_meteo_client import fetch_weather


from src.database.weather_repository import (
    complete_pipeline_run,
    fail_pipeline_run,
    get_locations,
    start_pipeline_run,
    upsert_weather_records,
)


# ============================================================
# Logging configuration
# ============================================================

# Configure timestamped log messages.
logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

# Create a logger specifically for this module.
logger = logging.getLogger(__name__)


# ============================================================
# File configuration
# ============================================================

# Project root is two levels above this file.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Base directory for original API JSON responses.
RAW_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "open_meteo"
)

# Name stored in metadata.pipeline_runs.
PIPELINE_NAME = "open_meteo_weather_ingestion"


def save_raw_weather(
    weather_json: dict[str, Any],
    province_code: str,
    ingestion_time: datetime,
) -> Path:
    """
    Save one original Open-Meteo response.

    Files are partitioned by ingestion date and hour.

    Example:
        data/raw/open_meteo/
            ingestion_date=2026-07-14/
                ingestion_hour=06/
                    province_code=01.json
    """

    # strftime() converts a datetime into formatted text.
    ingestion_date = ingestion_time.strftime("%Y-%m-%d")
    ingestion_hour = ingestion_time.strftime("%H")

    # Create a partition-style directory.
    output_directory = (
        RAW_DATA_PATH
        / f"ingestion_date={ingestion_date}"
        / f"ingestion_hour={ingestion_hour}"
    )

    # Create all required folders.
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Include minutes and seconds so repeated runs in the same hour
    # do not overwrite one another.
    timestamp_text = ingestion_time.strftime(
        "%Y%m%dT%H%M%SZ"
    )

    output_path = (
        output_directory
        / (
            f"province_code={province_code}"
            f"_{timestamp_text}.json"
        )
    )

    # Write the original API response without transformation.
    with output_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            weather_json,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path


def transform_weather_response(
    weather_json: dict[str, Any],
    location_id: int,
    ingestion_time: datetime,
) -> list[dict[str, Any]]:
    """
    Convert Open-Meteo hourly JSON into database-ready records.
    """

    # Extract the hourly section.
    hourly_data = weather_json["hourly"]

    # Each hourly array becomes one DataFrame column.
    weather_df = pd.DataFrame(hourly_data)

    required_columns = {
        "time",
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "rain",
        "wind_speed_10m",
        "wind_gusts_10m",
        "surface_pressure",
        "weather_code",
    }

    missing_columns = (
        required_columns
        - set(weather_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Open-Meteo hourly response is missing columns: "
            f"{sorted(missing_columns)}"
        )

    # utc=True creates timezone-aware UTC timestamps.
    weather_df["time"] = pd.to_datetime(
        weather_df["time"],
        utc=True,
        errors="coerce",
    )

    # Reject invalid timestamps rather than inserting bad data.
    if weather_df["time"].isna().any():
        raise ValueError(
            "Open-Meteo returned one or more invalid timestamps."
        )

    numeric_columns = [
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "rain",
        "wind_speed_10m",
        "wind_gusts_10m",
        "surface_pressure",
        "weather_code",
    ]

    for column in numeric_columns:
        weather_df[column] = pd.to_numeric(
            weather_df[column],
            errors="coerce",
        )

    # Rainfall and precipitation must not be negative.
    if weather_df["rain"].dropna().lt(0).any():
        raise ValueError(
            "Open-Meteo returned negative rain values."
        )

    if weather_df["precipitation"].dropna().lt(0).any():
        raise ValueError(
            "Open-Meteo returned negative precipitation values."
        )

    records: list[dict[str, Any]] = []

    # Iterate over each row and convert it into a dictionary for database insertion.
    for row in weather_df.itertuples(
        index=False
    ):
        records.append(
            {
                "location_id": location_id,

                # Use the same ingestion timestamp for all rows in this run.
                "forecast_time": row.time.to_pydatetime(),


                "ingested_at": ingestion_time,

                "temperature_c": (
                    None
                    if pd.isna(row.temperature_2m)
                    else float(row.temperature_2m)
                ),

                "relative_humidity_percent": (
                    None
                    if pd.isna(row.relative_humidity_2m)
                    else float(row.relative_humidity_2m)
                ),

                "precipitation_mm": (
                    None
                    if pd.isna(row.precipitation)
                    else float(row.precipitation)
                ),

                "rain_mm": (
                    None
                    if pd.isna(row.rain)
                    else float(row.rain)
                ),

                "wind_speed_kmh": (
                    None
                    if pd.isna(row.wind_speed_10m)
                    else float(row.wind_speed_10m)
                ),

                "wind_gusts_kmh": (
                    None
                    if pd.isna(row.wind_gusts_10m)
                    else float(row.wind_gusts_10m)
                ),

                "surface_pressure_hpa": (
                    None
                    if pd.isna(row.surface_pressure)
                    else float(row.surface_pressure)
                ),

                "weather_code": (
                    None
                    if pd.isna(row.weather_code)
                    else int(row.weather_code)
                ),
            }
        )

    return records


def run_weather_pipeline() -> None:
    """
    Run the end-to-end database weather ingestion.
    """

    ingestion_time = datetime.now(
        timezone.utc
    ).replace(microsecond=0)

    run_id: int | None = None
    rows_extracted = 0
    rows_loaded = 0

    try:
        run_id = start_pipeline_run(
            PIPELINE_NAME
        )

        logger.info(
            "Started pipeline run_id=%s",
            run_id,
        )

        locations_df = get_locations()

        location_count = len(locations_df)

        logger.info(
            "Loaded %s locations from PostgreSQL",
            location_count,
        )

        if location_count != 34:
            raise ValueError(
                f"Expected 34 monitoring locations, "
                f"but found {location_count}."
            )

        for location in locations_df.itertuples(
            index=False
        ):
            logger.info(
                "Fetching province=%s code=%s",
                location.province_name,
                location.province_code,
            )

            weather_json = fetch_weather(
                latitude=float(location.latitude),
                longitude=float(location.longitude),
                forecast_days=7,
            )

            raw_path = save_raw_weather(
                weather_json=weather_json,
                province_code=str(
                    location.province_code
                ),
                ingestion_time=ingestion_time,
            )

            logger.info(
                "Saved raw response to %s",
                raw_path,
            )

            records = transform_weather_response(
                weather_json=weather_json,
                location_id=int(location.location_id),
                ingestion_time=ingestion_time,
            )

            rows_extracted += len(records)

            loaded_count = upsert_weather_records(
                records
            )

            rows_loaded += loaded_count

            logger.info(
                "Processed province=%s rows=%s",
                location.province_name,
                loaded_count,
            )

        complete_pipeline_run(
            run_id=run_id,
            rows_extracted=rows_extracted,
            rows_loaded=rows_loaded,
        )

        logger.info(
            "Pipeline completed successfully: "
            "run_id=%s extracted=%s loaded=%s",
            run_id,
            rows_extracted,
            rows_loaded,
        )

    except Exception as error:
        if run_id is not None:
            fail_pipeline_run(
                run_id=run_id,
                error_message=str(error),
                rows_extracted=rows_extracted,
                rows_loaded=rows_loaded,
            )

        logger.exception(
            "Pipeline failed: run_id=%s",
            run_id,
        )
        raise


def main() -> None:
    """
    Command-line entry point.
    """

    run_weather_pipeline()


if __name__ == "__main__":
    main()
