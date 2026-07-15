# StormWatch Vietnam v2

StormWatch Vietnam is a PostgreSQL, dbt Core, and Streamlit weather-risk pipeline for Vietnam's 34 provincial-level administrative units.

> The risk scores are educational prototypes. Do not use them as official forecasts or disaster warnings.

## Architecture

```text
Open-Meteo
    -> raw.weather_hourly
    -> dbt staging and rolling-rain models
    -> analytics_marts.fact_risk_scores
    -> analytics_marts.province_risk_snapshot
    -> Streamlit dashboard
```

## Included dbt project

The `dbt/` directory contains five models:

- `stg_locations`
- `stg_weather_hourly`
- `int_weather_rolling_rain`
- `fact_risk_scores`
- `province_risk_snapshot`

Schema tests and two singular tests validate identifiers, required values, accepted risk levels, relationships, non-negative rainfall, and the expected 34-province snapshot.

## Prerequisites

- Python 3.10 or newer
- Docker Desktop

## Quick start

From the repository root:

```powershell
Copy-Item .env.example .env
Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

docker compose -f compose.yml up -d
python -m src.database.create_tables
python -m src.database.load_locations
python -m src.ingestion.ingest_weather_to_postgres
dbt build --project-dir dbt --profiles-dir dbt
python -m streamlit run dashboard/app.py
```

Change the example password in both `.env` and `.streamlit/secrets.toml` before starting PostgreSQL. Both files are ignored by Git.

Open the dashboard at `http://localhost:8501`.

## Configuration

`dbt/profiles.yml` reads these environment variables:

| Variable | Default |
|---|---|
| `DB_HOST` | `localhost` |
| `DB_PORT` | `5432` |
| `DB_NAME` | `stormwatch` |
| `DB_USER` | `stormwatch_user` |
| `DB_PASSWORD` | Required |

The Python ingestion code reads the same values from `.env`.

## Useful commands

```powershell
# Check configuration and database connectivity
dbt debug --project-dir dbt --profiles-dir dbt

# Build all models and execute all tests
dbt build --project-dir dbt --profiles-dir dbt

# Stop PostgreSQL but retain its data volume
docker compose -f compose.yml down

# Remove the local database volume and start over
docker compose -f compose.yml down -v
```

## Warehouse schemas

| Schema | Purpose |
|---|---|
| `raw` | Versioned Open-Meteo forecasts |
| `analytics` | Location source data |
| `analytics_staging` | Cleaned dbt views |
| `analytics_intermediate` | Rolling rainfall calculations |
| `analytics_marts` | Dashboard-ready risk tables |
| `metadata` | Pipeline execution history |

## Project layout

```text
dashboard/                 Streamlit database dashboard
dbt/                       dbt project, models, and tests
docker/postgres/init.sql   PostgreSQL bootstrap schema
src/clients/               Open-Meteo client
src/config/                Environment configuration
src/database/              PostgreSQL setup and repository functions
src/ingestion/             Database weather-ingestion pipeline
compose.yml                Local PostgreSQL service
```
