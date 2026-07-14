
    
    



select ingested_at
from "stormwatch"."analytics_staging"."stg_weather_hourly"
where ingested_at is null


