"""
This script converts hourly risk forecast into a province-level risk snapshot for each province in Vietnam.

Input: data/processed/fact_risk_hourly.csv
Output: data/processed/risk_snapshot.csv

The ouput contains 1 row for each province, shows the latest forecast time, and the maximum 
risk level in the forecast period (next 7 days) for each province. 
"""

from pathlib import Path
import pandas as pd

# ============================================================
# File configuration
# ============================================================

INPUT_PATH = Path("data/processed/fact_risk_hourly.csv")
DIM_PROVINCE_PATH = Path("data/processed/dim_province.csv")
OUTPUT_PATH = Path("data/processed/risk_snapshot.csv")

# Read and validate the hourly weather data from CSV file
# Returns a DataFrame 
def load_risk_data()->pd.DataFrame:

    # Check if the input file exists
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}\n "
                                "Check the filename or run the risk engine first.")
    
    # Read province_code as text
    risk_df = pd.read_csv(INPUT_PATH, dtype={"province_code": str})

    # Merge province coordinates from dimension table for map visualization.
    if DIM_PROVINCE_PATH.exists():
        dim_df = pd.read_csv(
            DIM_PROVINCE_PATH,
            dtype={"province_code": str},
            usecols=lambda col: col in {"province_code", "latitude", "longitude"},
        )
        risk_df = risk_df.merge(dim_df, on="province_code", how="left")

    # List the columns required to calculate the risk snapshot
    required_columns = {
        "province_code",
        "province_name",
        "forecast_time",
        "combined_score",
        "combined_risk_level",
    }

    # Find the required columns that are missing from the CSV
    missing_columns = required_columns - set(risk_df.columns)

    # Stop the program with error message if any required columns are missing
    if missing_columns:
        raise ValueError(f"Missing required columns in the input CSV: {sorted(missing_columns)}")

    # Convert forecast_time to datetime for proper sorting and comparison
    risk_df["forecast_time"] = pd.to_datetime(risk_df["forecast_time"], errors="coerce",)
    
    # Convert combined_score to numeric, coercing errors to NaN
    risk_df["combined_score"] = pd.to_numeric(risk_df["combined_score"], errors="coerce",)

    # Remove rows that are invalid becasue of missing or invalid data
    risk_df = risk_df.dropna(subset=["forecast_time", "combined_score"])

    # Sort the rows by province, risk score, and forecast time to prepare for snapshot calculation
    # ascending=False means that the highest risk score will come first for each province
    # ascending=True means that the latest forecast time will come first for each province
    risk_df = risk_df.sort_values(
        by=["province_code", "combined_score", "forecast_time"],
        ascending=[True, False, True],
    )

    return risk_df

# Select the highest risk level for each province and the latest forecast time
def peak_risk_snapshot(risk_df: pd.DataFrame)->pd.DataFrame:

    # Group the DataFrame by province_code and select the first row for each province group
    # The first row contains the highest risk score and the latest forecast time due to the previous sorting
    snapshot_df = (
        risk_df.groupby("province_code", as_index=False).first()
    )
    
    # Rename columns to match the desired output format
    snapshot_df = snapshot_df.rename(columns={
      "forecast_time": "peak_risk_time",
        "combined_score": "peak_risk_score",
        "combined_risk_level": "peak_risk_level",
    })

    # Add a status priority -> Higher values represent higher risk levels
    risk_level_priority = {
        "Low": 0,
        "Moderate": 1,
        "High": 2,
        "Extreme": 3,
    }

    # Map the risk levels to their corresponding priority values
    snapshot_df["alert_priority"] = (
        snapshot_df["peak_risk_level"]
        .map(risk_level_priority)
        .fillna(0)
        .astype(int)
    )

    # Add a boolean field for provinces requiring immediate attention (High or Extreme risk levels)
    snapshot_df["requires_attention"] = (
        snapshot_df["alert_priority"] >= 2
    )

    # Choose and order the columns for the final snapshot DataFrame
    preferred_columns = [
        "province_code",
        "province_name",
        "latitude",
        "longitude",
        "peak_risk_time",
        "rain_rate",
        "rain_6h",
        "rain_24h",
        "wind_gust_rate",
        "surface_pressure",
        "weather_code",
        "rain_score",
        "rain_risk_level",
        "storm_score",
        "storm_risk_level",
        "flood_score",
        "flood_risk_level",
        "peak_risk_score",
        "peak_risk_level",
        "alert_priority",
        "requires_attention",
        "ingested_at",
    ]

    # Keep only the preferred columns that exist in the DataFrame
    available_columns = [col for col in preferred_columns if col in snapshot_df.columns]
    snapshot_df = snapshot_df[available_columns]

    # Sort the final ouput: highest risk level first, then alphabetically by province name
    snapshot_df = snapshot_df.sort_values(
        by=["alert_priority", "province_name"],
        ascending=[False, True],
    )
    return snapshot_df

# Run basic quality checks on the snapshot DataFrame to ensure data integrity
def quality_check(snapshot_df: pd.DataFrame):

    # Check that there are 34 provinces in the snapshot DataFrame
    if len(snapshot_df) != 34:
        raise ValueError(f"Expected 34 provinces in the snapshot, but found {len(snapshot_df)}.")
    
    # Check that each province code appears only once in the snapshot DataFrame
    dup_counts = snapshot_df["province_code"].duplicated().sum()
    if dup_counts > 0:
        raise ValueError(f"Found {dup_counts} duplicate province codes in the snapshot.")
    
    # Check if any province is missing coordinates (latitude or longitude) in the snapshot DataFrame
    coordinate_cols = ["latitude", "longitude"]

    if set(coordinate_cols).issubset(snapshot_df.columns):
        missing_coords = snapshot_df[coordinate_cols].isna().any(axis=1).sum()
        if missing_coords > 0:
            raise ValueError(f"Found {missing_coords} provinces with missing coordinates in the snapshot.")
        
# Save the snapshot DataFrame to a CSV file 
def save_snapshot(snapshot_df: pd.DataFrame):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    snapshot_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Snapshot saved to {OUTPUT_PATH}")

# run the entire risk snapshot pipeline: load, process, quality check, and save
def main():

    # Load the hourly risk data from CSV
    risk_df = load_risk_data()
    print(f"Loaded {len(risk_df)} rows of hourly risk data from {INPUT_PATH}")

    # Select the peak risk snapshot for each province
    snapshot_df = peak_risk_snapshot(risk_df)

    # Run quality checks on the snapshot DataFrame
    quality_check(snapshot_df)

    # Save the snapshot DataFrame to a CSV file
    save_snapshot(snapshot_df)

    print(f"Risk snapshot completed. {len(snapshot_df)} provinces processed.")

    # Display the risk-level summary
    print("\nPeak risk summary:")
    print(snapshot_df["peak_risk_level"].value_counts().sort_index())

    # Count province requiring immediate attention (High or Extreme risk levels)
    attention_count = snapshot_df["requires_attention"].sum()

    print(f"\nProvinces requiring immediate attention (High or Extreme risk levels): {attention_count}")

    print(f"Saved risk snapshot to {OUTPUT_PATH}")

    print(f"\nRisk snapshot pipeline completed successfully.")

# run the main function if this script is executed directly
if __name__ == "__main__":
    main()