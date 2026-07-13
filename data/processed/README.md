# Processed Data Contract

This folder contains normalized outputs for the weather risk pipeline.

## Tables

### dim_province.csv
- Grain: 1 row per province
- Primary key: province_code
- Columns: province_code, province_name, latitude, longitude

### fact_weather_hourly.csv
- Grain: 1 row per province per forecast hour
- Recommended key: (province_code, forecast_time)
- Foreign key: province_code -> dim_province.province_code
- Main measures: weather observations and rolling rainfall with units in headers
- Unit examples: rain_mm, rain_6h_mm, rain_24h_mm, wind_speed_kmh, wind_gust_kmh, surface_pressure_hpa

### fact_risk_hourly.csv
- Grain: 1 row per province per forecast hour
- Recommended key: (province_code, forecast_time)
- Foreign key: province_code -> dim_province.province_code
- Main measures: risk scores and risk levels

## Join Patterns

- Join weather and risk facts:
  - keys: province_code, forecast_time
- Join any fact to province dimension:
  - key: province_code

## Notes

- Legacy file risk_scores.csv has been removed to avoid denormalized duplication.
- Source weather input remains weather_hourly.csv.
