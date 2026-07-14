/*
Purpose:
Calculate rolling six-hour and 24-hour rainfall totals.

Grain:
One row per province and forecast hour.
*/

SELECT
    weather_id,
    location_id,
    province_code,
    province_name,
    latitude,
    longitude,
    forecast_time,
    ingested_at,
    temperature_c,
    relative_humidity_percent,
    precipitation_mm,
    rain_mm,
    wind_speed_kmh,
    wind_gusts_kmh,
    surface_pressure_hpa,
    weather_code,
    source_name,

    /*
    The current row plus five preceding hourly records
    gives a six-record rolling window.
    */
    SUM(COALESCE(rain_mm, 0)) OVER (
        PARTITION BY location_id
        ORDER BY forecast_time
        ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
    ) AS rain_6h_mm,

    /*
    The current row plus 23 preceding records gives
    a 24-record rolling window.
    */
    SUM(COALESCE(rain_mm, 0)) OVER (
        PARTITION BY location_id
        ORDER BY forecast_time
        ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
    ) AS rain_24h_mm

FROM "stormwatch"."analytics_staging"."stg_weather_hourly"