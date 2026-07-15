/*
Return one highest-risk forecast hour per province.

Grain:
One row per province.
*/

WITH ranked_province_risks AS (

    SELECT
        *,

        /*
        Highest disaster risk receives row number 1.

        When two hours have the same risk score,
        the earlier forecast hour is selected.
        */
        ROW_NUMBER() OVER (
            PARTITION BY location_id
            ORDER BY
                disaster_risk_score DESC,
                forecast_time ASC
        ) AS province_risk_rank

    FROM {{ ref('fact_risk_scores') }}

)

SELECT
    location_id,
    province_code,
    province_name,
    latitude,
    longitude,

    forecast_time AS peak_risk_time,
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
    rain_risk_level,
    storm_risk_score,
    storm_risk_level,
    flood_risk_score,
    flood_risk_level,

    disaster_risk_score AS peak_risk_score,
    disaster_risk_level AS peak_risk_level,

    /*
    High and Extreme provinces require attention.
    */
    CASE
        WHEN disaster_risk_score >= 2 THEN TRUE
        ELSE FALSE
    END AS requires_attention

FROM ranked_province_risks

WHERE province_risk_rank = 1