"""
This script reads 34 provinces from CSV,
get latitude and longitude from OpenStreetMap API, 
and save a new enriched CSV with the coordinates.

Input: data/reference/vietnam_34_provinces.csv
Output: data/reference/dim_location.csv
"""

import time
import requests
import pandas as pd
from pathlib import Path

INPUT_PATH = Path("data/reference/vietnam_34_provinces.csv")
OUTPUT_PATH = Path("data/reference/dim_location.csv")
GEOCODING_URL = "https://nominatim.openstreetmap.org/search"

# convert the province name to latitude and longitude using OpenStreetMap API
def geocode_location(province_name):
    query = f"{province_name}, Vietnam" # add "Vietnam" to the query to improve accuracy

    # Qury parameters for the API request
    params = {
        "q": query,
        "format": "json",
        "limit": 1
    }

    # headers provide information about the application
    headers = {
        "User-Agent": "Stormwatch-Vietnam/1.0 (Data Engineer portfolio project)"
    }

    # Send GET request to the OpenStreetMap API
    response = requests.get(GEOCODING_URL, params=params, headers=headers, timeout=30)

    # Stop the program if API returns an error
    response.raise_for_status()

    #Convert JSON response to a Python objects.
    results = response.json()

    #If no results found, return empty values.
    if not results:
        return None, None
    
    # Get the first/best result.
    best_match = results[0]

    # Nominate returns latude and longitude as strings to convert to float.
    latitude = float(best_match["lat"])
    longitude = float(best_match["lon"])

    return latitude, longitude

# Read province from CSV, add coordinates, and save to a new CSV
def enrich_locations():
    # Read the existing CSV file into a pandas DataFrame
    provinces_df = pd.read_csv(INPUT_PATH)

    # Empty lists to store the latitude and longitude values
    latitudes = []
    longitudes = [] 

    # Loop through each province in the DataFrame 
    for index, row in provinces_df.iterrows():

        # Get the province name from the current row
        province_name = row["province_name"]
        print(f"Geocoding {province_name}...")

        # Call the geocoding function.
        latitude, longitude = geocode_location(province_name)

        # Store results
        latitudes.append(latitude)
        longitudes.append(longitude)

        # Wait 1 second before next request to avoid hitting the API rate limit
        time.sleep(1)

    # Add the latitude and longitude columns to the DataFrame
    provinces_df["latitude"] = latitudes
    provinces_df["longitude"] = longitudes

    # Save the enriched DataFrame to a new CSV file
    provinces_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig") # Use UTF-8 with BOM for compatibility with Excel

    print(f"Enriched location data saved to {OUTPUT_PATH}")

# Main function to run the enrichment pipeline
def main():
    print("Starting location enrichment...\n")
    enrich_locations()
    print("Location enrichment completed.")

# Run main() only when this file is executed directly
if __name__ == "__main__":
    main()




