
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        peak_risk_level as value_field,
        count(*) as n_records

    from "stormwatch"."analytics_marts"."province_risk_snapshot"
    group by peak_risk_level

)

select *
from all_values
where value_field not in (
    'Low','Moderate','High','Extreme'
)



  
  
      
    ) dbt_internal_test