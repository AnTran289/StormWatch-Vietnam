
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select rain_mm
from "stormwatch"."raw"."weather_hourly"
where rain_mm is null



  
  
      
    ) dbt_internal_test