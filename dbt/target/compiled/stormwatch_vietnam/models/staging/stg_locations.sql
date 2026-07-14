/*
Clean and standardise Vietnam location records.

Source:
analytics.dim_locations
*/

SELECT
    -- Internal PostgreSQL location identifier.
    location_id,

    -- Province code is an identifier rather than a measurement.
    CAST(province_code AS VARCHAR) AS province_code,

    -- TRIM removes leading and trailing spaces.
    TRIM(province_name) AS province_name,

    TRIM(province_name_en) AS province_name_en,

    TRIM(administrative_unit) AS administrative_unit,

    TRIM(administrative_region) AS administrative_region,

    -- Convert coordinates into standard decimal values.
    CAST(latitude AS NUMERIC(9, 6)) AS latitude,

    CAST(longitude AS NUMERIC(9, 6)) AS longitude,

    created_at,
    updated_at

FROM "stormwatch"."analytics"."dim_locations"