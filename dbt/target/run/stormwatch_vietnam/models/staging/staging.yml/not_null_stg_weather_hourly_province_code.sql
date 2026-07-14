
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select province_code
from "stormwatch"."analytics_staging"."stg_weather_hourly"
where province_code is null



  
  
      
    ) dbt_internal_test