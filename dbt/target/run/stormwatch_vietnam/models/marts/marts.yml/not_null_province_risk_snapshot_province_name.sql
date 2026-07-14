
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select province_name
from "stormwatch"."analytics_marts"."province_risk_snapshot"
where province_name is null



  
  
      
    ) dbt_internal_test