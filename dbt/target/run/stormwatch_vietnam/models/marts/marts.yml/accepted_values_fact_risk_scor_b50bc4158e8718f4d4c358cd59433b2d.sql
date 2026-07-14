
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        disaster_risk_level as value_field,
        count(*) as n_records

    from "stormwatch"."analytics_marts"."fact_risk_scores"
    group by disaster_risk_level

)

select *
from all_values
where value_field not in (
    'Low','Moderate','High','Extreme'
)



  
  
      
    ) dbt_internal_test