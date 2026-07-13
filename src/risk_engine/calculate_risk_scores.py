"""
This script reads hourly weather forecast data from CSV, and calculates protoype:

1. Rain risk
2. Storm risk
3. Flood indicator
4. Combined disaster risk 

Input: data/processed/weather_hourly.csv
Output:
- data/processed/dim_province.csv
- data/processed/fact_weather_hourly.csv
- data/processed/fact_risk_hourly.csv
"""

from pathlib import Path
import pandas as pd

# ============================================================
# File configuration
# ============================================================

INPUT_PATH = Path("data/processed/weather_hourly.csv")
DIM_PROVINCE_PATH = Path("data/processed/dim_province.csv")
FACT_WEATHER_PATH = Path("data/processed/fact_weather_hourly.csv")
FACT_RISK_PATH = Path("data/processed/fact_risk_hourly.csv")

# ============================================================
# Prototype risk thresholds
# ============================================================

RAIN_RISK_THRESHOLD = {
    "moderate": 5.0,
    "high": 15.0,
    "extreme": 30.0  # mm/hr
}

WIND_GUST_THRESHOLD = {
    "moderate": 40.0,
    "high": 65.0,
    "extreme": 90.0  # km/h
}

RAIN_6H_THRESHOLD = {
    "moderate": 25.0,
    "high": 50.0,
    "extreme": 90.0,# mm/6h
}

RAIN_24H_THRESHOLD = {
    "moderate": 50.0,
    "high": 100.0,
    "extreme": 200.0, # mm/24h
}

# ============================================================
# Reusable helper functions
# ============================================================

# Convert numeric weather value to risk score.
def score_from_threshold(value: float, moderate: float, high: float, extreme: float) -> int:

    """"
    Score meaning:
    0 = Low
    1 = Moderate
    2 = High
    3 = Extreme

    Parameters:
    value: The weather value to be scored.
    moderate: The minimum threshold for moderate risk.
    high: The minimum threshold for high risk.
    extreme: The minimum threshold for extreme risk.

    Returns:
    int: The risk score.
    """

    # Check the highest threshold first to ensure correct scoring.
    if value >= extreme:
        return 3
    elif value >= high:
        return 2
    elif value >= moderate:
        return 1
    else:
        return 0
    
# Convert a numeric score to a readable risk level string.
def score_to_risk_level(score: int) -> str:

    # A dictionary mapping scores to risk level strings.
    risk_levels = {
        0: "Low",
        1: "Moderate",
        2: "High",
        3: "Extreme"
    }

    # Return the corresponding risk level string, or "Unknown" if the score is not in the dictionary.
    return risk_levels.get(score, "Unknown")

# Calculate hourly rain risk score based on the rain rate (mm/hr).
def calculate_rain_risk(rain_rate: float) -> int:
    return score_from_threshold(
        value=rain_rate,
        moderate=RAIN_RISK_THRESHOLD["moderate"],
        high=RAIN_RISK_THRESHOLD["high"],
        extreme=RAIN_RISK_THRESHOLD["extreme"]
    )

# Calculate a storm indicator
def calculate_storm_score(wind_gust_rate: float, rain_rate: float, weather_code: int) -> int:

    # Calculate wind gust risk score
    wind_gust_score = score_from_threshold(
        value=wind_gust_rate,
        moderate=WIND_GUST_THRESHOLD["moderate"],
        high=WIND_GUST_THRESHOLD["high"],
        extreme=WIND_GUST_THRESHOLD["extreme"]
    )

    # Calculate rain risk score
    rain_score = calculate_rain_risk(rain_rate)

    # Open-Meteo weather codes indicating storm conditions (e.g., thunderstorm, hail, etc.)
    storm_weather_codes = {95, 96, 99}

    # Start with no storm risk
    storm_score = 0

    # Increase the storm score if the forecast code indicates a storm
    if weather_code in storm_weather_codes:
        storm_score = 2

    # Use highest score, this means if any of the conditions are severe, the storm score will reflect that even if the other conditions are mild.
    return max(wind_gust_score, rain_score, storm_score)

# Calculate rainfall-based flood indicator based on 6-hour and 24-hour periods.
def calculate_flood_score(rain_6h: float, rain_24h: float) -> int:

    # Calculate 6-hour rain risk score
    rain_6h_score = score_from_threshold(
        value=rain_6h,
        moderate=RAIN_6H_THRESHOLD["moderate"],
        high=RAIN_6H_THRESHOLD["high"],
        extreme=RAIN_6H_THRESHOLD["extreme"]
    )

    # Calculate 24-hour rain risk score
    rain_24h_score = score_from_threshold(
        value=rain_24h,
        moderate=RAIN_24H_THRESHOLD["moderate"],
        high=RAIN_24H_THRESHOLD["high"],
        extreme=RAIN_24H_THRESHOLD["extreme"]
    )

    # Use the highest score to indicate flood risk
    return max(rain_6h_score, rain_24h_score)

# Calculate one overall disaster risk score based on rain, storm, and flood scores.
def calculate_combined_score(rain_score: int, storm_score: int, flood_score: int) -> int:

    # Use the highest score among rain, storm, and flood to indicate overall disaster risk
    return max(rain_score, storm_score, flood_score)

# ============================================================
# Data preparation
# ============================================================

# Read and validate the input CSV file, and return a DataFrame with the necessary columns.
def load_weather_data() -> pd.DataFrame:

    # Check if the input file exists
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}\n"
                                "Run fetch_weather.py first.")
    
    # dtype keeps province codes as text to prevent a code from becoming the integer
    weather_df = pd.read_csv(INPUT_PATH, dtype = {"province_code": "string"},)
    
    # Normalize known schema aliases from upstream ingestion.
    column_aliases = {
        "rain_rate": ["rain_rate", "rain_mm", "precipitation_mm"],
        "wind_gust_rate": ["wind_gust_rate", "wind_gusts_kmh"],
        "ingested_at": ["ingested_at", "data_fetched_at"],
        "surface_pressure": ["surface_pressure", "surface_pressure_hpa", "sureface_pressure"],
    }

    rename_map = {}
    for canonical_name, candidates in column_aliases.items():
        if canonical_name in weather_df.columns:
            continue
        matched_name = next((name for name in candidates if name in weather_df.columns), None)
        if matched_name:
            rename_map[matched_name] = canonical_name

    if rename_map:
        weather_df = weather_df.rename(columns=rename_map)

    # Define the columns 
    required_columns = {
        "province_code",
        "province_name",
        "forecast_time",
        "rain_rate",
        "wind_gust_rate",
        "weather_code",
    }
    
    # Find any required columns missing from the input files
    missing_columns = required_columns - set(weather_df.columns)

    if missing_columns:
        raise ValueError("The weather file is missing required columns: "
                         f"{sorted(missing_columns)}")
    
    # Convert forecast_time from text into pandas datetime values
    weather_df["forecast_time"] = pd.to_datetime(
        weather_df["forecast_time"],
        errors="coerce"
    )

    # Convert weather measurement columns to numeric values
    numeric_columns = ["rain_rate", "wind_gust_rate", "weather_code",]

    for column in numeric_columns:
        weather_df[column] = pd.to_numeric(
            weather_df[column],
            errors="coerce"
        )
    
    # Remove rows with no valid timestamp
    weather_df = weather_df.dropna(
        subset=["forecast_time"],
    )
    
    # Replace missing weather measurements with zero
    weather_df[numeric_columns] = weather_df[numeric_columns].fillna(0)

    # Sort observations before calculating totals
    weather_df = weather_df.sort_values(
        by = ["province_code", "forecast_time"],
    ).reset_index(drop=True)

    return weather_df

# Add 6-hour and 24-hour columns.
def add_accumulated_rainfall(
        weather_df: pd.DataFrame,
)->pd.DataFrame:

    # Create a copy so the original Dataframe is not modified
    result_df = weather_df.copy()
    
    # seperate the data by province to calculate rolling sums
    # returns a result wityh the same index as the original DataFrame
    result_df["rain_6h"] = (
        result_df.groupby("province_code")["rain_rate"]
        .transform(lambda x: x.rolling(window=6, min_periods=1).sum())
    )

    # Calculate rolling 24-hour rain totals for each province
    result_df["rain_24h"] = (
        result_df.groupby("province_code")["rain_rate"]
        .transform(lambda x: x.rolling(window=24, min_periods=1).sum())
    )

    return result_df

# ============================================================
# Risk calculation
# ============================================================

def calculate_risk_scores(weather_df: pd.DataFrame) -> pd.DataFrame:

    # Create a copy of the DataFrame to avoid modifying the original
    risk_df = weather_df.copy()

    # Calculate rain risk score
    risk_df["rain_score"] = risk_df["rain_rate"].apply(calculate_rain_risk)

    # Calculate storm risk score
    risk_df["storm_score"] = risk_df.apply(
        lambda row: calculate_storm_score(
            wind_gust_rate=row["wind_gust_rate"],
            rain_rate=row["rain_rate"],
            weather_code=row["weather_code"]
        ),
        axis=1, # run once for each row
    )

    # Calculate flood indicator score
    risk_df["flood_score"] = risk_df.apply(
        lambda row: calculate_flood_score(
            rain_6h=row["rain_6h"],
            rain_24h=row["rain_24h"]
        ),
        axis=1,
    )   

    # Calculate combined disaster risk score
    risk_df["combined_score"] = risk_df.apply(
        lambda row: calculate_combined_score(
            rain_score=row["rain_score"],
            storm_score=row["storm_score"],
            flood_score=row["flood_score"]
        ),
        axis=1,
    )

    # Create human-readable risk level columns for each score
    risk_df["rain_risk_level"] = risk_df["rain_score"].apply(score_to_risk_level)

    risk_df["storm_risk_level"] = risk_df["storm_score"].apply(score_to_risk_level)

    risk_df["flood_risk_level"] = risk_df["flood_score"].apply(score_to_risk_level)

    risk_df["combined_risk_level"] = risk_df["combined_score"].apply(score_to_risk_level)

    return risk_df

# ============================================================
# Save output
# ============================================================

def _select_existing_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    existing_columns = [column for column in columns if column in df.columns]
    return df[existing_columns].copy()


# Save normalized outputs: one province dimension and two fact tables.
def save_outputs(risk_df: pd.DataFrame) -> None:

    # Create the output directory if it doesn't exist
    FACT_RISK_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Province dimension: one row per province
    dim_columns = [
        "province_code",
        "province_name",
        "latitude",
        "longitude",
    ]
    dim_province_df = (
        _select_existing_columns(risk_df, dim_columns)
        .drop_duplicates(subset=["province_code"])
        .sort_values(by=["province_code"])
    )
    dim_province_df.to_csv(
        DIM_PROVINCE_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # Weather fact table at province-hour grain
    weather_columns = [
        "province_code",
        "forecast_time",
        "ingested_at",
        "temperature_c",
        "humidity_percent",
        "rain_rate",
        "rain_6h",
        "rain_24h",
        "wind_speed_kmh",
        "wind_gust_rate",
        "surface_pressure",
        "weather_code",
    ]
    fact_weather_df = _select_existing_columns(risk_df, weather_columns)

    # Rename exported weather columns to include measurement units.
    weather_export_names = {
        "rain_rate": "rain_mm",
        "rain_6h": "rain_6h_mm",
        "rain_24h": "rain_24h_mm",
        "wind_gust_rate": "wind_gust_kmh",
        "surface_pressure": "surface_pressure_hpa",
    }
    fact_weather_df = fact_weather_df.rename(columns=weather_export_names)

    fact_weather_df.to_csv(
        FACT_WEATHER_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # Risk fact table at province-hour grain
    risk_columns = [
        "province_code",
        "province_name",
        "forecast_time",
        "rain_score",
        "rain_risk_level",
        "storm_score",
        "storm_risk_level",
        "flood_score",
        "flood_risk_level",
        "combined_score",
        "combined_risk_level",
    ]
    fact_risk_df = _select_existing_columns(risk_df, risk_columns)
    fact_risk_df.to_csv(
        FACT_RISK_PATH,
        index=False,
        encoding="utf-8-sig",
    )

# ============================================================
# Main pipeline
# ============================================================

# Run the risk score calculation pipeline: load data, calculate scores, and save results.
def main() -> None:

    print("Starting risk score calculation pipeline...\n")

    # Load the weather data from CSV
    weather_df = load_weather_data()
    print(f"Loaded {len(weather_df)} rows of weather data.")

    # Add accumulated rainfall columns (6-hour and 24-hour)
    weather_df = add_accumulated_rainfall(weather_df)
    print("Added accumulated rainfall columns.")

    # Calculate risk scores based on the weather data
    risk_df = calculate_risk_scores(weather_df)
    print("Calculated risk scores.")

    # Save dimension and fact tables
    save_outputs(risk_df)
    print(f"Saved province dimension to {DIM_PROVINCE_PATH}")
    print(f"Saved weather facts to {FACT_WEATHER_PATH}")
    print(f"Saved risk facts to {FACT_RISK_PATH}")

    # Count rows in each risk level category for combined risk
    risk_level_counts = (risk_df["combined_risk_level"].value_counts())

    print("\nRisk summary (combined risk levels):")
    print(risk_level_counts)

    print(f"\nRisk rows created: {len(risk_df)}")
    print(f"Saved province dimension to {DIM_PROVINCE_PATH}")
    print(f"Saved weather facts to {FACT_WEATHER_PATH}")
    print(f"Saved risk facts to {FACT_RISK_PATH}")
    print("\nRisk score calculation pipeline completed.")

# execute the main function if this script is run directly
if __name__ == "__main__":
    main()

