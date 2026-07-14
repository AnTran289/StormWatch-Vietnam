
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select peak_risk_time
from "stormwatch"."analytics_marts"."province_risk_snapshot"
where peak_risk_time is null



  
  
      
    ) dbt_internal_test