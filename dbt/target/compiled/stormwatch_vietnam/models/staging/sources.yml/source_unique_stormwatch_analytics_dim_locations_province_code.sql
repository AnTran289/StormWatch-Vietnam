
    
    

select
    province_code as unique_field,
    count(*) as n_records

from "stormwatch"."analytics"."dim_locations"
where province_code is not null
group by province_code
having count(*) > 1


