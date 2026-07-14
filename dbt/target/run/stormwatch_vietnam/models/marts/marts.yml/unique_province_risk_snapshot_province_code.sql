
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    province_code as unique_field,
    count(*) as n_records

from "stormwatch"."analytics_marts"."province_risk_snapshot"
where province_code is not null
group by province_code
having count(*) > 1



  
  
      
    ) dbt_internal_test