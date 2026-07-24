# StormWatch Vietnam — Version 3

StormWatch Vietnam is a data-engineering portfolio project that transforms hourly weather forecasts into prototype rainfall, storm, and flood-risk indicators for Vietnam's 34 provincial-level administrative units.

Version 3 uses **Airflow** for orchestration, **PostgreSQL** as its data warehouse, **dbt Core** for transformation and testing, and **Streamlit** for interactive analytics.

> **Disclaimer:** This project is for educational and portfolio purposes. Its risk indicators are experimental and must not be used as official weather forecasts or disaster warnings.

## Architecture

```text
Airflow scheduler (hourly)
       |
       v
Open-Meteo weather ingestion
       |
       v
PostgreSQL source schemas
|-- raw.weather_hourly
`-- analytics.dim_locations
       |
       v
dbt staging views
|-- analytics_staging.stg_locations
`-- analytics_staging.stg_weather_hourly
       |
       v
dbt intermediate view
`-- analytics_intermediate.int_weather_rolling_rain
       |
       v
dbt analytics marts
|-- analytics_marts.fact_risk_scores
`-- analytics_marts.province_risk_snapshot
       |
       v
Streamlit dashboard
```

Airflow executes `start_run -> fetch_weather -> load_postgres -> dbt_build -> finish_run`. Pipeline execution metadata is stored separately in `metadata.pipeline_runs` and displayed by the dashboard.

## Data Warehouse

PostgreSQL separates source data, transformations, reporting marts, and operational metadata into purpose-specific schemas.

| Schema | Responsibility |
|---|---|
| `raw` | Versioned hourly weather forecasts |
| `analytics` | Core location dimension used by dbt sources |
| `analytics_staging` | Cleaned and deduplicated dbt staging views |
| `analytics_intermediate` | Reusable calculations such as rolling rainfall |
| `analytics_marts` | Dashboard-ready risk tables |
| `metadata` | Pipeline execution history and health information |

### Source Tables

#### `analytics.dim_locations`

Contains the 34 monitored provincial-level units, including:

- Internal `location_id`
- Province code and Vietnamese/English names
- Administrative unit and region
- Latitude and longitude
- Creation and update timestamps

#### `raw.weather_hourly`

Stores versioned hourly forecasts, including:

- Location and forecast timestamps
- Ingestion timestamp
- Temperature and relative humidity
- Precipitation and rain
- Wind speed and wind gusts
- Surface pressure
- Open-Meteo weather code
- Source name

Multiple forecast versions can exist for the same location and forecast hour. dbt selects the newest record using `ingested_at`, with `weather_id` as a deterministic tie-breaker.

## dbt Model Layers

The dbt project contains five models arranged into staging, intermediate, and mart layers.

| Model | Schema | Materialization | Grain | Purpose |
|---|---|---|---|---|
| `stg_locations` | `analytics_staging` | View | One row per location | Cleans province identifiers, names, administrative metadata, and coordinates. |
| `stg_weather_hourly` | `analytics_staging` | View | One row per location and forecast hour | Deduplicates forecast versions and joins location metadata. |
| `int_weather_rolling_rain` | `analytics_intermediate` | View | One row per location and forecast hour | Calculates rolling 6-hour and 24-hour rainfall. |
| `fact_risk_scores` | `analytics_marts` | Table | One row per location and forecast hour | Calculates rain, storm, flood, and combined risk indicators. |
| `province_risk_snapshot` | `analytics_marts` | Table | One row per province | Selects the highest-risk forecast hour for dashboard reporting. |

The latest local dbt execution log records:

- 5 models
- 2 sources
- 44 data tests
- 5,712 hourly rows in `fact_risk_scores`
- 34 province rows in `province_risk_snapshot`

## Transformation Logic

### Latest Forecast Selection

`stg_weather_hourly` uses `ROW_NUMBER()` over each `location_id` and `forecast_time`. Records are ordered by the latest `ingested_at` and then the highest `weather_id`, ensuring that downstream models use only the newest available forecast version.

### Rolling Rainfall

`int_weather_rolling_rain` calculates:

- `rain_6h_mm`: the current record plus the previous five hourly records
- `rain_24h_mm`: the current record plus the previous 23 hourly records

Windows are partitioned by `location_id` and ordered by `forecast_time`.

### Prototype Risk Scores

Risk scores use four levels:

| Score | Level |
|---:|---|
| 0 | Low |
| 1 | Moderate |
| 2 | High |
| 3 | Extreme |

| Indicator | Moderate | High | Extreme |
|---|---:|---:|---:|
| Hourly rain | 5 mm | 15 mm | 30 mm |
| Wind gust | 40 km/h | 65 km/h | 90 km/h |
| Rolling 6-hour rain | 25 mm | 50 mm | 80 mm |
| Rolling 24-hour rain | 50 mm | 100 mm | 200 mm |

Open-Meteo codes `95`, `96`, and `99` produce a High thunderstorm score.

- The **storm score** is the maximum of wind, hourly rain, and thunderstorm scores.
- The **flood score** is the maximum of the 6-hour and 24-hour rainfall scores.
- The **disaster score** is the maximum of rain, storm, and flood scores.

### Province Snapshot

`province_risk_snapshot` selects one highest-risk forecast hour per province. When multiple hours share the same score, the earliest forecast hour is selected. Provinces with a High or Extreme score are marked with `requires_attention = true`.

## Dashboard

The Streamlit dashboard queries the PostgreSQL marts directly and provides:

- National risk metrics
- Province monitoring map
- Risk-level distribution
- Priority-province table
- Accent-insensitive province search
- Province-level rainfall, wind, and risk charts
- Complete province snapshot table
- Recent pipeline-run status

Dashboard queries are cached for five minutes. Users can clear the cache with the dashboard's refresh control.

The dashboard reads:

- `analytics_marts.province_risk_snapshot`
- `analytics_marts.fact_risk_scores`
- `metadata.pipeline_runs`

## Project Structure

```text
stormwatch-vietnam/
|-- airflow/
|   |-- dags/
|   |   `-- stormwatch_pipeline.py  # Scheduled and manual Airflow DAGs
|   |-- Dockerfile
|   `-- requirements.txt
|-- dashboard/
|   `-- app.py                       # PostgreSQL-backed Streamlit dashboard
|-- dbt/
|   |-- models/
|   |   |-- staging/
|   |   |-- intermediate/
|   |   `-- marts/
|   |-- tests/
|   |-- dbt_project.yml
|   `-- profiles.yml
|-- docker/
|   `-- postgres/
|       `-- init.sql                 # PostgreSQL schema bootstrap
|-- src/
|   |-- ingestion/
|   `-- warehouse/
|       `-- load_postgres.py         # Idempotent PostgreSQL loader
|-- .env.example
|-- compose.yaml
|-- requirements.txt
`-- README.md
```

## Prerequisites

- Python 3.10 or newer
- Docker Desktop (the Compose stack runs PostgreSQL and Airflow)
- dbt Core with the PostgreSQL adapter
- Streamlit, SQLAlchemy, and the PostgreSQL driver

## Orchestrate with Airflow

The Airflow integration runs the PostgreSQL/dbt pipeline every hour:

```text
start_run -> fetch_weather -> load_postgres -> dbt_build -> finish_run
```

It also provides the manually triggered `stormwatch_refresh_locations` DAG for
refreshing the province list and coordinates. Keeping this separate avoids
calling the rate-limited geocoding service during every weather run.

Create the local environment file, change the example password, then build and
start the stack from the repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose logs airflow
```

Open `http://localhost:8080`. The username is `admin`; retrieve its generated
password with:

```powershell
docker compose exec airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

Enable and trigger `stormwatch_weather_pipeline` in the Airflow UI. Its schedule is
`0 * * * *` in the `Asia/Ho_Chi_Minh` timezone, catch-up is disabled, and
only one run can be active at a time.

Useful commands:

```powershell
# Verify that Airflow can parse the DAGs
docker compose exec airflow airflow dags list

# Trigger the weather pipeline from the CLI
docker compose exec airflow airflow dags trigger stormwatch_weather_pipeline

# Stop Airflow while preserving its metadata volume
docker compose down
```

The Compose stack starts PostgreSQL first and waits for it to become healthy.
The loader then creates the required schemas/tables when absent, upserts the location
dimension, preserves versioned forecasts in `raw.weather_hourly`, and records
success/failure plus row counts in `metadata.pipeline_runs`. The Airflow
container connects to the `postgres` Compose service using the `DB_*` values
from `.env`.

The repository is mounted at `/opt/airflow/project` inside the container, so
pipeline outputs written beneath `data/` remain available on the host. This
Compose setup is intended for local development; use the official Helm chart
or a managed Airflow service for a production deployment.

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the required packages:

```powershell
python -m pip install -r requirements.txt
```

## Configure dbt

Configure a profile named `stormwatch_vietnam`. Environment variables keep credentials out of version control:

```yaml
stormwatch_vietnam:
  target: dev
  outputs:
    dev:
      type: postgres
      host: "{{ env_var('DB_HOST') }}"
      port: "{{ env_var('DB_PORT', '5432') | int }}"
      user: "{{ env_var('DB_USER') }}"
      password: "{{ env_var('DB_PASSWORD') }}"
      dbname: "{{ env_var('DB_NAME', 'stormwatch') }}"
      schema: analytics
      threads: 4
```

The source relations `analytics.dim_locations` and `raw.weather_hourly` must exist before dbt runs.

## Run dbt

Run commands from the repository root:

```powershell
dbt debug --project-dir dbt --profiles-dir dbt
dbt build --project-dir dbt --profiles-dir dbt
```

Useful development commands:

```powershell
# Run transformations only
dbt run --project-dir dbt --profiles-dir dbt

# Run data tests only
dbt test --project-dir dbt --profiles-dir dbt

# Build one mart and all of its upstream dependencies
dbt build --select +fact_risk_scores --project-dir dbt --profiles-dir dbt

# Generate dbt documentation
dbt docs generate --project-dir dbt --profiles-dir dbt
dbt docs serve --project-dir dbt --profiles-dir dbt
```

## Configure and Run Streamlit

Set the database environment variables before starting Streamlit. The dashboard
uses the same `DB_*` variables as dbt and the warehouse loader:

```powershell
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$env:DB_NAME = "stormwatch"
$env:DB_USER = "your_username"
$env:DB_PASSWORD = "your_password"
```

Start the dashboard:

```powershell
python -m streamlit run dashboard/app.py
```

## Limitations

- Flood risk is based on forecast rainfall accumulation only.
- River levels, soil moisture, terrain, drainage capacity, and official emergency-warning data are not included.
- Thresholds are experimental and have not been validated for operational alerting.
- Dashboard availability depends on fresh warehouse data and successful dbt builds.

## Author

**An Tran** 

Data Engineering Portfolio Project

[GitHub](https://github.com/AnTran289)
