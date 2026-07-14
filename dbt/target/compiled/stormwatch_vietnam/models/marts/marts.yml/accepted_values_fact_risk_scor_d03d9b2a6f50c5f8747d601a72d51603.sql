
    
    

with all_values as (

    select
        rain_risk_level as value_field,
        count(*) as n_records

    from "stormwatch"."analytics_marts"."fact_risk_scores"
    group by rain_risk_level

)

select *
from all_values
where value_field not in (
    'Low','Moderate','High','Extreme'
)


