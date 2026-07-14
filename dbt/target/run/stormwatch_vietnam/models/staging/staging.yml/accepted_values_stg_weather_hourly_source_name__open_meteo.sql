
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        source_name as value_field,
        count(*) as n_records

    from "stormwatch"."analytics_staging"."stg_weather_hourly"
    group by source_name

)

select *
from all_values
where value_field not in (
    'open_meteo'
)



  
  
      
    ) dbt_internal_test