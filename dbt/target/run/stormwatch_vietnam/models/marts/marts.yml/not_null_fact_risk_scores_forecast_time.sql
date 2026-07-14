
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select forecast_time
from "stormwatch"."analytics_marts"."fact_risk_scores"
where forecast_time is null



  
  
      
    ) dbt_internal_test