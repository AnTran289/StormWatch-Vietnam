
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select latitude
from "stormwatch"."analytics"."dim_locations"
where latitude is null



  
  
      
    ) dbt_internal_test