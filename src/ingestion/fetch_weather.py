"""
This script reads Vietnam's 34 enriched locations from dim_locations.csv,
calls Open-Meteo for each lcoation, saves the raw JSON response, and 
creates a clean hourly weather CSV file for each location. 

Input: data/reference/dim_locations.csv
Output: data/raw/open_meteo/
        data/processed/weather_hourly.csv
"""

import json
import time # pause between API calls to avoid rate limiting
import requests # call Open-Meteo API
import pandas as pd
from pathlib import Path
from datetime import datetime # create timestamp for raw JSON file names

# ===========================
# Configuration
# ===========================

LOCATIONS_PATH = Path("data/reference/dim_location.csv")
RAW_OUTPUT_DIR = Path("data/raw/open_meteo/")
PROCESSED_OUTPUT_PATH = Path("data/processed/weather_hourly.csv")
OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"

# Weather variables to request from Open-Meteo API
HOURLY_VARIABLES = [
    "temperature_2m",
    "relativehumidity_2m",
    "precipitation",
    "rain",
    "wind_speed_10m",
    "wind_gusts_10m",
    "surface_pressure",
    "weather_code",
]

# Call Open-Meteo API for a given location and return the JSON response
def fetch_weather_data(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(HOURLY_VARIABLES), # join the list of variables into a comma-separated string
        "timezone": "Asia/Ho_Chi_Minh",
        "forecast_days": 7, # get 7 days of forecast data
    }

    # Send GET request to Open-Meteo API
    response = requests.get(OPEN_METEO_API_URL, params=params, timeout=30)
    response.raise_for_status() # Stop execution if the request fails (e.g., network error, 4xx or 5xx response)
    return response.json() # Convert the response to JSON and return it

# Saw the raw JSON response to a file in the specified output directory
def save_raw_json(data, province_code):

    # Create raw output folder if it doesn't exist
    RAW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True) # create the output directory if it doesn't exist
    
    # Create a timestamp for the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Build the output file path using the province code and timestamp
    output_file_path = RAW_OUTPUT_DIR / f"{province_code}_{timestamp}.json"

    # Save the JSON data to the output file
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2) 

    return output_file_path # Return the path of the saved file 

# Convert one Open-Meteo JSON response into a pandas DataFrame table
def transform_weather_data(weather_json, location_row):
    hourly_data = weather_json.get("hourly", {}) # ectract the "hourly" section of the JSON response
    weather_df = pd.DataFrame(hourly_data) # convert the hourly data into a DataFrame
    
    # Add location metadata so every row links back to a province
    weather_df["province_code"] = location_row["province_code"]
    weather_df["province_name"] = location_row["province_name"]
    weather_df["latitude"] = location_row["latitude"]
    weather_df["longitude"] = location_row["longitude"]

    # Rename columns to match database naming style
    weather_df = weather_df.rename(columns={
        "time": "forecast_time",
        "temperature_2m": "temperature_c",
        "relativehumidity_2m": "humidity_percent",
        "precipitation": "precipitation_mm",
        "rain": "rain_mm",
        "wind_speed_10m": "wind_speed_kmh",
        "wind_gusts_10m": "wind_gusts_kmh",
        "surface_pressure": "surface_pressure_hpa",
        "weather_code": "weather_code"
    })

    # Add a timestamp column to indicate when the data was fetched
    weather_df["data_fetched_at"] = datetime.now().isoformat(timespec="seconds")

    return weather_df

# Weather ingestion process: read locations, fetch weather data, save raw JSON, transform to DataFrame, and save to CSV
def run_weather_ingestion():
    locations_df = pd.read_csv(LOCATIONS_PATH) # Read the locations CSV into a DataFrame
    all_weather_frames = [] # Store DataFrames fromm all provinces
    
    # Loop through each location, fetch weather data, save raw JSON, transform to DataFrame, and collect all DataFrames
    for index, location_row in locations_df.iterrows():
        province_code = location_row["province_code"]
        lat = location_row["latitude"]
        lon = location_row["longitude"]
        province_name = location_row["province_name"]

        print(f"Fetching weather data for {location_row['province_name']} (code: {province_code}) at ({lat}, {lon})...")

        # Fetch weather data from Open-Meteo API
        weather_json = fetch_weather_data(lat, lon)

        # Save the raw JSON response to a file
        raw_json_path = save_raw_json(weather_json, province_code)
        print(f"Saved raw JSON to {raw_json_path}")

        # Transform the JSON response into a DataFrame
        weather_df = transform_weather_data(weather_json, location_row)
        all_weather_frames.append(weather_df) # Collect the DataFrame

        time.sleep(0.5) # Pause for 0.5 seconds to avoid hitting API rate limits

    # Combineall province DataFrames into a single DataFrame
    combined_weather_df = pd.concat(all_weather_frames, ignore_index=True)

    # Create processed output folder if it doesn't exist
    PROCESSED_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save the combined DataFrame to a CSV file
    combined_weather_df.to_csv(PROCESSED_OUTPUT_PATH, index=False, encoding="utf-8")

    print(f"\nWeather ingestion completed.")
    print(f"Rows created: {len(combined_weather_df)}")
    print(f"Saved processed weather data to {PROCESSED_OUTPUT_PATH}")

# Entry point for the script
def main():
    print("Starting weather ingestion process...")
    run_weather_ingestion()

# Run the main function if this script is executed directly
if __name__ == "__main__":
    main()

    
