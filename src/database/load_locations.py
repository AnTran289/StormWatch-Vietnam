"""
Load Vietnam province locations from CSV into PostgreSQL.

Input: data/reference/dim_location.csv
Output: analytics.dim_location
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.database.connection import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCATIONS_CSV_PATH = PROJECT_ROOT / "data/reference/dim_location.csv"


def load_locations_csv() -> pd.DataFrame:
    """Read and validate the location CSV before database load."""
    # If the file is missing, fail early with a clear error.
    if not LOCATIONS_CSV_PATH.exists():
        raise FileNotFoundError(f"Locations CSV file not found: {LOCATIONS_CSV_PATH}")

    # Keep province codes as text so leading zeros are not lost.
    df = pd.read_csv(LOCATIONS_CSV_PATH, dtype={"province_code": "string"})

    required_columns = {
        "province_code",
        "province_name",
        "latitude",
        "longitude",
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns in locations CSV: {sorted(missing_columns)}")

    # Turn coordinates into numbers so bad values can be caught.
    for col in ["latitude", "longitude"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    text_columns = [
        "province_code",
        "province_name",
        "province_name_en",
        "administrative_unit",
        "administrative_region",
    ]
    # Trim extra spaces from text fields.
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # Core fields must always have values.
    required_value_columns = ["province_code", "province_name", "latitude", "longitude"]
    if df[required_value_columns].isna().any().any():
        raise ValueError("Some required values are null in the locations CSV file.")

    # This project currently expects 34 provinces.
    province_count = df["province_code"].nunique()
    if province_count != 34:
        raise ValueError(f"Expected 34 province codes, but found {province_count}.")

    # Province codes must be unique.
    duplicate_codes = df[df.duplicated(subset=["province_code"], keep=False)]
    if not duplicate_codes.empty:
        duplicate_list = duplicate_codes["province_code"].tolist()
        raise ValueError(f"Duplicate province codes found in locations CSV: {duplicate_list}")

    # Quick sanity check for Vietnam coordinate ranges.
    if not df["latitude"].between(8, 24).all():
        raise ValueError("One or more latitude values are outside the expected range.")
    if not df["longitude"].between(102, 110).all():
        raise ValueError("One or more longitude values are outside the expected range.")

    return df


def _to_nullable(value):
    # Convert pandas missing values to None for SQL inserts.
    return None if pd.isna(value) else value


def upsert_locations(df: pd.DataFrame) -> int:
    """Upsert location rows into analytics.dim_location and return rows processed."""
    # Make sure province_code is unique so ON CONFLICT works.
    ensure_unique_sql = text(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_location_province_code
        ON analytics.dim_location (province_code);
        """
    )

    upsert_sql = text(
        """
        INSERT INTO analytics.dim_location (
            province_code,
            province_name,
            province_name_en,
            administrative_unit,
            administrative_region,
            latitude,
            longitude
        )
        VALUES (
            :province_code,
            :province_name,
            :province_name_en,
            :administrative_unit,
            :administrative_region,
            :latitude,
            :longitude
        )
        ON CONFLICT (province_code) DO UPDATE SET
            province_name = EXCLUDED.province_name,
            province_name_en = EXCLUDED.province_name_en,
            administrative_unit = EXCLUDED.administrative_unit,
            administrative_region = EXCLUDED.administrative_region,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            updated_at = CURRENT_TIMESTAMP;
        """
    )

    # Build parameter dictionaries from each CSV row.
    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "province_code": _to_nullable(row["province_code"]),
                "province_name": _to_nullable(row["province_name"]),
                "province_name_en": _to_nullable(row.get("province_name_en")),
                "administrative_unit": _to_nullable(row.get("administrative_unit")),
                "administrative_region": _to_nullable(row.get("administrative_region")),
                "latitude": _to_nullable(row["latitude"]),
                "longitude": _to_nullable(row["longitude"]),
            }
        )

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(ensure_unique_sql)
        conn.execute(upsert_sql, records)

    return len(records)


def count_locations() -> int:
    # Used at the end to confirm data is in the table.
    count_sql = text("SELECT COUNT(*) FROM analytics.dim_location;")
    engine = get_engine()
    with engine.connect() as conn:
        return conn.execute(count_sql).scalar_one()


def main() -> None:
    # Main flow: read CSV, upsert rows, then check final count.
    print("Loading location CSV...")
    df = load_locations_csv()
    print(f"Loaded {len(df)} records from CSV.")

    rows_processed = upsert_locations(df)
    database_count = count_locations()

    print(f"Rows processed by upsert: {rows_processed}")
    print(f"Rows currently in PostgreSQL: {database_count}")

    if database_count != 34:
        raise ValueError("PostgreSQL does not contain exactly 34 locations.")

    print("Location ingestion completed successfully.")


if __name__ == "__main__":
    main()
