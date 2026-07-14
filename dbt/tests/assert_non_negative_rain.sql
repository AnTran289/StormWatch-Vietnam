/*
Fail if any cleaned weather row contains negative rainfall.
*/

SELECT
    weather_id,
    rain_mm,
    precipitation_mm

FROM {{ ref('stg_weather_hourly') }}

WHERE rain_mm < 0
   OR precipitation_mm < 0