
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    weather_id as unique_field,
    count(*) as n_records

from "stormwatch"."analytics_marts"."fact_risk_scores"
where weather_id is not null
group by weather_id
having count(*) > 1



  
  
      
    ) dbt_internal_test