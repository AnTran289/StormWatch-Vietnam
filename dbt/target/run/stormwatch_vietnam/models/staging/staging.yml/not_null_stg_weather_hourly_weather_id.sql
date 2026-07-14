
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select weather_id
from "stormwatch"."analytics_staging"."stg_weather_hourly"
where weather_id is null



  
  
      
    ) dbt_internal_test