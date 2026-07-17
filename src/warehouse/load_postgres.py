"""Load StormWatch CSV outputs into PostgreSQL and track pipeline runs."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


LOCATIONS_PATH = Path("data/reference/dim_location.csv")
WEATHER_PATH = Path("data/processed/weather_hourly.csv")
PIPELINE_NAME = "stormwatch_weather_pipeline"


def connect():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "stormwatch"),
        user=os.getenv("DB_USER", "stormwatch_user"),
        password=os.environ["DB_PASSWORD"],
        connect_timeout=10,
    )


def ensure_schema(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS analytics")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS raw")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS metadata")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics.dim_locations (
                location_id INTEGER NOT NULL,
                province_code VARCHAR NOT NULL,
                province_name VARCHAR NOT NULL,
                province_name_en VARCHAR,
                administrative_unit VARCHAR,
                administrative_region VARCHAR,
                latitude NUMERIC(9, 6),
                longitude NUMERIC(9, 6),
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS raw.weather_hourly (
                weather_id BIGINT NOT NULL,
                location_id INTEGER NOT NULL,
                forecast_time TIMESTAMPTZ NOT NULL,
                ingested_at TIMESTAMPTZ NOT NULL,
                temperature_c NUMERIC,
                relative_humidity_percent NUMERIC,
                precipitation_mm NUMERIC,
                rain_mm NUMERIC,
                wind_speed_kmh NUMERIC,
                wind_gusts_kmh NUMERIC,
                surface_pressure_hpa NUMERIC,
                weather_code INTEGER,
                source_name VARCHAR NOT NULL DEFAULT 'open_meteo'
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata.pipeline_runs (
                run_id BIGSERIAL PRIMARY KEY,
                pipeline_name VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMPTZ,
                records_processed INTEGER DEFAULT 0,
                error_message TEXT,
                rows_extracted INTEGER NOT NULL DEFAULT 0,
                rows_loaded INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cursor.execute(
            "ALTER TABLE metadata.pipeline_runs ADD COLUMN IF NOT EXISTS airflow_run_id VARCHAR"
        )
        cursor.execute(
            """
            UPDATE raw.weather_hourly
            SET source_name = 'open_meteo'
            WHERE LOWER(REPLACE(source_name, '-', '_')) = 'open_meteo'
              AND source_name <> 'open_meteo'
            """
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS pipeline_runs_airflow_run_id_idx "
            "ON metadata.pipeline_runs (airflow_run_id) WHERE airflow_run_id IS NOT NULL"
        )
    connection.commit()


def load_locations(connection) -> dict[str, int]:
    if not LOCATIONS_PATH.exists():
        raise FileNotFoundError(f"Location file not found: {LOCATIONS_PATH}")

    locations = pd.read_csv(LOCATIONS_PATH, dtype={"province_code": "string"})
    required = {"province_code", "province_name", "latitude", "longitude"}
    missing = required - set(locations.columns)
    if missing:
        raise ValueError(f"Location file is missing columns: {sorted(missing)}")

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT province_code, location_id FROM analytics.dim_locations"
        )
        location_ids = {str(code): location_id for code, location_id in cursor.fetchall()}
        cursor.execute("SELECT COALESCE(MAX(location_id), 0) FROM analytics.dim_locations")
        next_id = cursor.fetchone()[0] + 1

        for row in locations.to_dict("records"):
            code = str(row["province_code"])
            unit = row.get("division_type")
            if code in location_ids:
                cursor.execute(
                    """
                    UPDATE analytics.dim_locations
                    SET province_name = %s, administrative_unit = %s,
                        latitude = %s, longitude = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE location_id = %s
                    """,
                    (row["province_name"], unit, row["latitude"], row["longitude"], location_ids[code]),
                )
            else:
                location_ids[code] = next_id
                cursor.execute(
                    """
                    INSERT INTO analytics.dim_locations (
                        location_id, province_code, province_name, administrative_unit,
                        latitude, longitude, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (next_id, code, row["province_name"], unit, row["latitude"], row["longitude"]),
                )
                next_id += 1

    connection.commit()
    return location_ids


def weather_id(province_code: str, forecast_time: str, ingested_at: str) -> int:
    key = f"{province_code}|{forecast_time}|{ingested_at}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big") & ((1 << 63) - 1)


def load_weather(connection, location_ids: dict[str, int]) -> tuple[int, int]:
    if not WEATHER_PATH.exists():
        raise FileNotFoundError(f"Weather file not found: {WEATHER_PATH}")

    weather = pd.read_csv(WEATHER_PATH, dtype={"province_code": "string"})
    aliases = {
        "relative_humidity_percent": "humidity_percent",
        "ingested_at": "data_fetched_at",
    }
    for target, source in aliases.items():
        if target not in weather.columns and source in weather.columns:
            weather[target] = weather[source]

    required = {"province_code", "forecast_time", "ingested_at", "rain_mm"}
    missing = required - set(weather.columns)
    if missing:
        raise ValueError(f"Weather file is missing columns: {sorted(missing)}")

    rows = []
    for row in weather.to_dict("records"):
        code = str(row["province_code"])
        if code not in location_ids:
            raise ValueError(f"Unknown province code in weather data: {code}")
        identifier = weather_id(code, str(row["forecast_time"]), str(row["ingested_at"]))
        rows.append(
            (
                identifier,
                location_ids[code],
                row["forecast_time"],
                row["ingested_at"],
                row.get("temperature_c"),
                row.get("relative_humidity_percent"),
                row.get("precipitation_mm"),
                row.get("rain_mm"),
                row.get("wind_speed_kmh"),
                row.get("wind_gusts_kmh"),
                row.get("surface_pressure_hpa"),
                row.get("weather_code"),
                "open_meteo",
            )
        )

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT weather_id FROM raw.weather_hourly WHERE weather_id = ANY(%s)",
            ([row[0] for row in rows],),
        )
        existing = {value for (value,) in cursor.fetchall()}
        new_rows = [row for row in rows if row[0] not in existing]
        if new_rows:
            execute_values(
                cursor,
                """
                INSERT INTO raw.weather_hourly (
                    weather_id, location_id, forecast_time, ingested_at,
                    temperature_c, relative_humidity_percent, precipitation_mm,
                    rain_mm, wind_speed_kmh, wind_gusts_kmh,
                    surface_pressure_hpa, weather_code, source_name
                ) OVERRIDING SYSTEM VALUE VALUES %s
                """,
                new_rows,
                page_size=1000,
            )
    connection.commit()
    return len(rows), len(new_rows)


def start_run(connection, airflow_run_id: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO metadata.pipeline_runs (pipeline_name, status, airflow_run_id)
            VALUES (%s, 'running', %s)
            ON CONFLICT (airflow_run_id) WHERE airflow_run_id IS NOT NULL
            DO UPDATE SET status = 'running', started_at = CURRENT_TIMESTAMP,
                          completed_at = NULL, error_message = NULL
            """,
            (PIPELINE_NAME, airflow_run_id),
        )
    connection.commit()


def finish_run(connection, airflow_run_id: str, status: str, error: str | None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE metadata.pipeline_runs
            SET status = %s, completed_at = CURRENT_TIMESTAMP,
                error_message = %s
            WHERE airflow_run_id = %s
            """,
            (status, error, airflow_run_id),
        )
    connection.commit()


def update_counts(connection, airflow_run_id: str, extracted: int, loaded: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE metadata.pipeline_runs
            SET records_processed = GREATEST(records_processed, %s),
                rows_extracted = GREATEST(rows_extracted, %s),
                rows_loaded = GREATEST(rows_loaded, %s)
            WHERE airflow_run_id = %s
            """,
            (loaded, extracted, loaded, airflow_run_id),
        )
    connection.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("start", "locations", "load", "finish"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--run-id", required=True)
        if command == "finish":
            command_parser.add_argument("--status", choices=("success", "failed"), required=True)
            command_parser.add_argument("--error")
    args = parser.parse_args()

    with connect() as connection:
        ensure_schema(connection)
        if args.command == "start":
            start_run(connection, args.run_id)
        elif args.command == "locations":
            locations = load_locations(connection)
            print(f"Loaded {len(locations)} locations")
        elif args.command == "load":
            locations = load_locations(connection)
            extracted, loaded = load_weather(connection, locations)
            update_counts(connection, args.run_id, extracted, loaded)
            print(f"Loaded {loaded} of {extracted} weather rows")
        elif args.command == "finish":
            finish_run(connection, args.run_id, args.status, args.error)


if __name__ == "__main__":
    main()
