"""
Call the Open-Meteo Forecast API and return parsed forecast data.
"""

import time
from typing import Any

import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "wind_speed_10m",
    "wind_gusts_10m",
    "surface_pressure",
    "weather_code",
]


def fetch_weather(
    latitude: float,
    longitude: float,
    forecast_days: int = 7,
    max_attempts: int = 3,
) -> dict[str, Any]:
    """Fetch an hourly forecast for one location."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "UTC",
        "forecast_days": forecast_days,
    }

    # Retry logic for API calls with exponential backoff
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                OPEN_METEO_URL,
                params=params,
                timeout=30,
            )
            response.raise_for_status()

            weather_json = response.json()
            if "hourly" not in weather_json:
                raise ValueError("Open-Meteo response does not contain hourly data.")

            return weather_json

        # Handle network errors and API response issues with retries
        except (requests.RequestException, ValueError):
            if attempt == max_attempts:
                raise

            delay_seconds = 2 ** attempt # Exponential backoff: 2, 4, 8 seconds for attempts 1, 2, 3
            print(
                f"API attempt {attempt} failed. "
                f"Retrying in {delay_seconds} seconds..."
            )
            time.sleep(delay_seconds)

    raise RuntimeError("Unexpected API retry state.")