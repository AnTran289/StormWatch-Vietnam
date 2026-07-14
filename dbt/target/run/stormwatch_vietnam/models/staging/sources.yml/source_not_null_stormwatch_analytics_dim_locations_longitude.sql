
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select longitude
from "stormwatch"."analytics"."dim_locations"
where longitude is null



  
  
      
    ) dbt_internal_test