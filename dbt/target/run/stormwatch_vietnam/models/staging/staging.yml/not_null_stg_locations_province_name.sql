
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select province_name
from "stormwatch"."analytics_staging"."stg_locations"
where province_name is null



  
  
      
    ) dbt_internal_test