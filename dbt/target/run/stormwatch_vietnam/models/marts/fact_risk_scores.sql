
  
    

  create  table "stormwatch"."analytics_marts"."fact_risk_scores__dbt_tmp"
  
  
    as
  
  (
    /*
Calculate prototype rain, storm, flood and combined risk scores.
*/

WITH risk_components AS (

    SELECT
        *,

        -- Hourly rainfall score.
        CASE
            WHEN rain_mm >= 30 THEN 3
            WHEN rain_mm >= 15 THEN 2
            WHEN rain_mm >= 5 THEN 1
            ELSE 0
        END AS rain_risk_score,

        -- Wind gust score.
        CASE
            WHEN wind_gusts_kmh >= 90 THEN 3
            WHEN wind_gusts_kmh >= 65 THEN 2
            WHEN wind_gusts_kmh >= 40 THEN 1
            ELSE 0
        END AS wind_risk_score,

        -- Thunderstorm weather-code score.
        CASE
            WHEN weather_code IN (95, 96, 99) THEN 2
            ELSE 0
        END AS thunderstorm_risk_score,

        -- Six-hour accumulated rainfall score.
        CASE
            WHEN rain_6h_mm >= 80 THEN 3
            WHEN rain_6h_mm >= 50 THEN 2
            WHEN rain_6h_mm >= 25 THEN 1
            ELSE 0
        END AS rain_6h_risk_score,

        -- 24-hour accumulated rainfall score.
        CASE
            WHEN rain_24h_mm >= 200 THEN 3
            WHEN rain_24h_mm >= 100 THEN 2
            WHEN rain_24h_mm >= 50 THEN 1
            ELSE 0
        END AS rain_24h_risk_score

    FROM "stormwatch"."analytics_intermediate"."int_weather_rolling_rain"

),

combined_components AS (

    SELECT
        *,

        /*
        GREATEST returns the largest supplied value.
        */
        GREATEST(
            wind_risk_score,
            rain_risk_score,
            thunderstorm_risk_score
        ) AS storm_risk_score,

        GREATEST(
            rain_6h_risk_score,
            rain_24h_risk_score
        ) AS flood_risk_score

    FROM risk_components

),

final_scores AS (

    SELECT
        *,

        GREATEST(
            rain_risk_score,
            storm_risk_score,
            flood_risk_score
        ) AS disaster_risk_score

    FROM combined_components

)

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
    rain_6h_mm,
    rain_24h_mm,
    wind_speed_kmh,
    wind_gusts_kmh,
    surface_pressure_hpa,
    weather_code,

    rain_risk_score,

    CASE rain_risk_score
        WHEN 3 THEN 'Extreme'
        WHEN 2 THEN 'High'
        WHEN 1 THEN 'Moderate'
        ELSE 'Low'
    END AS rain_risk_level,

    storm_risk_score,

    CASE storm_risk_score
        WHEN 3 THEN 'Extreme'
        WHEN 2 THEN 'High'
        WHEN 1 THEN 'Moderate'
        ELSE 'Low'
    END AS storm_risk_level,

    flood_risk_score,

    CASE flood_risk_score
        WHEN 3 THEN 'Extreme'
        WHEN 2 THEN 'High'
        WHEN 1 THEN 'Moderate'
        ELSE 'Low'
    END AS flood_risk_level,

    disaster_risk_score,

    CASE disaster_risk_score
        WHEN 3 THEN 'Extreme'
        WHEN 2 THEN 'High'
        WHEN 1 THEN 'Moderate'
        ELSE 'Low'
    END AS disaster_risk_level

FROM final_scores
  );
  