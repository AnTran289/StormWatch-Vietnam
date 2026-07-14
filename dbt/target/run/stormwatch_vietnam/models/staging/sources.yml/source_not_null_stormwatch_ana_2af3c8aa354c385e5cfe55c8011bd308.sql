
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select province_code
from "stormwatch"."analytics"."dim_locations"
where province_code is null



  
  
      
    ) dbt_internal_test