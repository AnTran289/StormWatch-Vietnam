/*
Custom data test.

A dbt data test succeeds when this query returns zero rows.
It fails when one or more rows are returned.
*/

SELECT
    COUNT(*) AS actual_province_count

FROM {{ ref('province_risk_snapshot') }}

HAVING COUNT(*) <> 34