
    
    

select
    weather_id as unique_field,
    count(*) as n_records

from "stormwatch"."raw"."weather_hourly"
where weather_id is not null
group by weather_id
having count(*) > 1


