# StormWatch Vietnam

StormWatch Vietnam is an end-to-end **Data Engineering** portfolio project that ingests public weather data, transforms it into prototype rainfall, storm, and flood-risk indicators, and serves interactive analytics for **Vietnam's 34 provincial-level administrative units**.

The project evolved from a CSV-based ETL pipeline into a modern analytics platform using **Python**, **PostgreSQL**, **dbt**, and **Streamlit**, with future plans for **Airflow** orchestration and cloud deployment.

> **Disclaimer:** This project is for educational and portfolio purposes only. The generated risk indicators are experimental and **must not** be used as official weather forecasts or disaster warnings.

---

## Architecture

```text
Public APIs
┌───────────────────────┐
| Vietnam Province API  |
| Open-Meteo API        |
| OpenStreetMap         |
└─────────┬─────────────┘
          |
          v
Python ingestion
          |
          v
Raw JSON storage
          |
          v
PostgreSQL data warehouse
(raw / analytics / metadata)
          |
          v
dbt transformations
(staging -> intermediate -> marts)
          |
          v
analytics_marts.province_risk_snapshot
          |
          v
Streamlit dashboard
```

---

## Features

### Data Ingestion

- Retrieve Vietnam's 34 provincial-level administrative units
- Enrich monitoring locations with latitude and longitude
- Collect seven-day hourly forecasts from Open-Meteo
- Preserve raw API responses as JSON
- Prepare weather data for warehouse loading

### Data Warehouse

- PostgreSQL schemas for raw data, analytics, and pipeline metadata
- Versioned hourly weather storage
- Province dimension
- Pipeline execution metadata

### dbt Transformations

| Model | Purpose |
|---|---|
| `stg_locations` | Clean province dimension |
| `stg_weather_hourly` | Select the latest weather forecast version |
| `int_weather_rolling_rain` | Calculate rolling rainfall |
| `fact_risk_scores` | Produce hourly risk indicators |
| `province_risk_snapshot` | Publish a dashboard-ready province summary |

### Dashboard

The Streamlit dashboard provides:

- National weather overview
- Rainfall, storm, and flood monitoring
- Interactive province map
- Province drill-down
- Hourly forecast charts
- Pipeline health monitoring

---

## Tech Stack

| Category | Technology |
|---|---|
| Language | Python |
| Database | PostgreSQL |
| Transformation | dbt Core |
| Dashboard | Streamlit |
| Data processing | pandas |
| APIs | Requests |
| Database connectivity | SQLAlchemy |
| Version control | Git and GitHub |
| Planned | Airflow and GitHub Actions |

---

## Data Pipeline

```text
Province API
     |
     v
Coordinate enrichment
     |
     v
Open-Meteo API
     |
     v
Raw JSON
     |
     v
PostgreSQL raw.weather_hourly
     |
     v
dbt staging -> intermediate -> marts
     |
     v
analytics_marts.province_risk_snapshot
     |
     v
Streamlit dashboard
```

---

## Prototype Risk Logic

Risk levels use a four-level scale:

| Score | Level |
|---:|---|
| 0 | Low |
| 1 | Moderate |
| 2 | High |
| 3 | Extreme |

Current thresholds:

| Indicator | Moderate | High | Extreme |
|---|---:|---:|---:|
| Hourly rainfall | 5 mm | 15 mm | 30 mm |
| Wind gust | 40 km/h | 65 km/h | 90 km/h |
| Rolling 6-hour rainfall | 25 mm | 50 mm | 80 mm |
| Rolling 24-hour rainfall | 50 mm | 100 mm | 200 mm |

The combined disaster score is calculated from rainfall, storm, and flood indicators. Provinces with **High** or **Extreme** risk are flagged as requiring attention.

---

## Project Structure

```text
stormwatch-vietnam/
|-- dashboard/
|   `-- app.py
|-- dbt/
|   |-- analyses/
|   |-- logs/
|   |-- seeds/
|   `-- snapshots/
|-- src/
|   |-- ingestion/
|   |   |-- coordinates_enrich.py
|   |   |-- fetch_vietnam_provinces.py
|   |   `-- fetch_weather.py
|   |-- risk_engine/
|   |   `-- calculate_risk_scores.py
|   `-- transformation/
|       `-- risk_snapshot.py
|-- data/
|   |-- analytics/
|   |-- processed/
|   |-- raw/
|   `-- reference/
`-- README.md
```

---

## Getting Started

### Clone the repository

```bash
git clone https://github.com/AnTran289/StormWatch-Vietnam.git
cd StormWatch-Vietnam
```

### Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

The current repository does not include a `requirements.txt`. Install the packages used by the database, dbt, and dashboard layers directly:

```powershell
pip install dbt-core dbt-postgres streamlit pandas altair sqlalchemy psycopg2-binary requests
```

### Run dbt

The dbt project directory is named `dbt`:

```powershell
dbt debug --project-dir dbt --profiles-dir dbt
dbt build --project-dir dbt --profiles-dir dbt
```

> **Current repository note:** The local `dbt` directory contains supporting directories and execution logs, but its `dbt_project.yml`, `profiles.yml`, and `models/` files are currently absent. Restore or add those files before running dbt.

### Run the dashboard

Configure the `stormwatch_db` connection in `.streamlit/secrets.toml`, then run:

```powershell
python -m streamlit run dashboard/app.py
```

The dashboard expects these PostgreSQL relations:

- `analytics_marts.province_risk_snapshot`
- `analytics_marts.fact_risk_scores`
- `metadata.pipeline_runs`

---

## Roadmap

- [x] CSV-based ETL prototype
- [x] PostgreSQL data warehouse
- [x] dbt transformations and testing
- [x] Streamlit analytics dashboard
- [ ] Airflow orchestration
- [ ] Incremental loading
- [ ] GitHub Actions CI/CD
- [ ] Object storage with MinIO or S3
- [ ] Cloud deployment

---

## Documentation

Detailed documentation is available in the project Wiki.

- 📖 https://github.com/AnTran289/StormWatch-Vietnam/wiki

---

## Author

**An Tran**

Data Engineering Portfolio Project
