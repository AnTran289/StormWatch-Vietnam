import requests
import pandas as pd
from pathlib import Path


# ===========================
# Configuration
# ===========================
API_URL = "https://provinces.open-api.vn/api/v2/p/"
OUTPUT_PATH = Path("data/reference/vietnam_34_provinces.csv")

# ===========================
# Extract
# ===========================

# Download the list of provinces/cities from the API and return the JSON data
def fetch_provinces():
    response = requests.get(API_URL, timeout=30) 
    response.raise_for_status() 
    return response.json()

# Convert the JSON data into a pandas DataFrame with the desired columns
def transform_provinces(data):
    rows = []

    for item in data:
        rows.append({
            "province_code": item.get("code"),
            "province_name": item.get("name"),
            "province_codename": item.get("codename"),
            "division_type": item.get("division_type"),
            "phone_code": item.get("phone_code")
        })

    return pd.DataFrame(rows)

# ===========================
# Load
# ===========================

#Save the DataFrame to a CSV file at the specified output path
def save_to_csv(df):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig") # Use UTF-8 with BOM for compatibility with Excel

# ===========================
# Main ETL Pipeline
# ===========================

def main():
    print("Starting province ingestion...\n")
    data = fetch_provinces() # Extract the data from the API
    print(data[0]) # print firts province returned from the API 
    df = transform_provinces(data) # Transform the data into a DataFrame

    print(f"Fetched {len(df)} provinces/cities")

    # Quality check: Ensure that the number of provinces/cities matches the expected count of 34
    if len(df) != 34:
        print("Warning: expected 34 provincial-level units")

    #Load the DataFrame to a CSV file
    save_to_csv(df)
    print(f"Saved to {OUTPUT_PATH}")

# Run main function if the script is executed directly
if __name__ == "__main__":
    main()