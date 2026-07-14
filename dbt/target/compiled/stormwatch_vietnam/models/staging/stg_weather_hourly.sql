/*
Purpose:
1. Clean raw Open-Meteo measurements
2. Keep the latest available forecast version
3. Add location metadata

Grain:
One row per location and forecast hour.
*/

WITH ranked_forecasts AS (

    SELECT
        weather_id,
        location_id,
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
        ROW_NUMBER assigns an order to forecast versions.

        The newest ingested_at value receives row number 1.
        */
        ROW_NUMBER() OVER (
            PARTITION BY
                location_id,
                forecast_time
            ORDER BY
                ingested_at DESC,
                weather_id DESC
        ) AS forecast_version_rank

    FROM "stormwatch"."raw"."weather_hourly"

),

latest_forecasts AS (

    SELECT
        weather_id,
        location_id,
        forecast_time,
        ingested_at,

        CAST(temperature_c AS NUMERIC(6, 2))
            AS temperature_c,

        CAST(relative_humidity_percent AS NUMERIC(6, 2))
            AS relative_humidity_percent,

        CAST(precipitation_mm AS NUMERIC(10, 2))
            AS precipitation_mm,

        CAST(rain_mm AS NUMERIC(10, 2))
            AS rain_mm,

        CAST(wind_speed_kmh AS NUMERIC(8, 2))
            AS wind_speed_kmh,

        CAST(wind_gusts_kmh AS NUMERIC(8, 2))
            AS wind_gusts_kmh,

        CAST(surface_pressure_hpa AS NUMERIC(8, 2))
            AS surface_pressure_hpa,

        weather_code,
        source_name

    FROM ranked_forecasts

    -- Keep only the latest version.
    WHERE forecast_version_rank = 1

)

SELECT
    weather.weather_id,
    weather.location_id,

    location.province_code,
    location.province_name,
    location.latitude,
    location.longitude,

    weather.forecast_time,
    weather.ingested_at,
    weather.temperature_c,
    weather.relative_humidity_percent,
    weather.precipitation_mm,
    weather.rain_mm,
    weather.wind_speed_kmh,
    weather.wind_gusts_kmh,
    weather.surface_pressure_hpa,
    weather.weather_code,
    weather.source_name

FROM latest_forecasts AS weather

INNER JOIN "stormwatch"."analytics_staging"."stg_locations" AS location
    ON weather.location_id = location.location_id