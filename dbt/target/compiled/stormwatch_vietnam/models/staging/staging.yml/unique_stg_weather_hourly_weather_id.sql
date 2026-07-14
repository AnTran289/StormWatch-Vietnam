
    
    

select
    weather_id as unique_field,
    count(*) as n_records

from "stormwatch"."analytics_staging"."stg_weather_hourly"
where weather_id is not null
group by weather_id
having count(*) > 1


