# StormWatch Vietnam — Version 1

StormWatch Vietnam is a CSV-based data engineering portfolio project that collects public weather forecasts for Vietnam's 34 provincial-level administrative units, transforms them into prototype weather-risk indicators, and presents the results in an interactive Streamlit dashboard.

Version 1 demonstrates an end-to-end batch pipeline using public APIs, Python, pandas, JSON and CSV storage, risk-scoring logic, geospatial data, and dashboard visualisation.

> **Disclaimer:** This educational project produces experimental indicators. Do not use it as an official disaster warning, evacuation guide, weather forecast, or emergency-management system.

## Pipeline

```text
Vietnam Provinces API
        ↓
data/reference/vietnam_34_provinces.csv
        ↓
OpenStreetMap Nominatim coordinate enrichment
        ↓
data/reference/dim_location.csv
        ↓
Open-Meteo seven-day hourly forecasts
        ↓
data/raw/open_meteo/*.json
        ↓
data/processed/weather_hourly.csv
        ↓
Risk calculation
        ├── data/processed/dim_province.csv
        ├── data/processed/fact_weather_hourly.csv
        └── data/processed/fact_risk_hourly.csv
        ↓
data/processed/risk_snapshot.csv
        ↓
Streamlit dashboard
```

The pipeline collects approximately `34 × 7 × 24 = 5,712` forecast rows per complete run.

## Features

- Ingests Vietnam's 34 current provincial-level administrative units.
- Enriches each province with a representative latitude and longitude.
- Collects seven days of hourly forecasts from Open-Meteo.
- Preserves original API responses as JSON.
- Calculates hourly rain, storm, flood, and combined risk indicators.
- Builds province, weather, and risk analytical CSV datasets.
- Selects the peak-risk forecast hour for each province.
- Displays national metrics, an interactive map, filters, priority tables, charts, province drilldowns, and CSV downloads in Streamlit.

## Technology

| Area | Technology |
| --- | --- |
| Language | Python |
| API requests | Requests |
| Data processing | pandas |
| Weather source | Open-Meteo |
| Province source | Vietnam Provinces Open API |
| Geocoding | OpenStreetMap Nominatim |
| Storage | JSON and CSV |
| Dashboard | Streamlit and PyDeck |

## Download Version 1

Download the latest CSV-pipeline release from the [GitHub Releases page](https://github.com/AnTran289/StormWatch-Vietnam/releases).

To clone this release directly:

```bash
git clone --branch v1.0.1 --depth 1 https://github.com/AnTran289/StormWatch-Vietnam.git
cd StormWatch-Vietnam
```

## Setup

Python 3.10 or newer is recommended.

### 1. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Quick Start

The release includes generated CSV files, so you can open the dashboard immediately:

```bash
python -m streamlit run dashboard/app.py
```

Then visit [http://localhost:8501](http://localhost:8501).

## Rebuild the Pipeline

Run all commands from the repository root:

```bash
python src/ingestion/fetch_vietnam_provinces.py
python src/ingestion/coordinates_enrich.py
python src/ingestion/fetch_weather.py
python src/risk_engine/calculate_risk_scores.py
python src/transformation/risk_snapshot.py
python -m streamlit run dashboard/app.py
```

Each stage depends on the previous stage's output.

### Pipeline stages

1. `fetch_vietnam_provinces.py` writes `data/reference/vietnam_34_provinces.csv`.
2. `coordinates_enrich.py` queries OpenStreetMap Nominatim and writes `data/reference/dim_location.csv`.
3. `fetch_weather.py` preserves API responses in `data/raw/open_meteo/` and writes `data/processed/weather_hourly.csv`.
4. `calculate_risk_scores.py` writes the province dimension and hourly weather/risk facts.
5. `risk_snapshot.py` selects the highest-risk forecast hour per province and writes `data/processed/risk_snapshot.csv`.

## Project Structure

```text
StormWatch-Vietnam/
├── dashboard/
│   └── app.py
├── data/
│   ├── analytics/
│   ├── processed/
│   ├── raw/open_meteo/
│   └── reference/
├── src/
│   ├── ingestion/
│   │   ├── fetch_vietnam_provinces.py
│   │   ├── coordinates_enrich.py
│   │   └── fetch_weather.py
│   ├── risk_engine/
│   │   └── calculate_risk_scores.py
│   └── transformation/
│       └── risk_snapshot.py
├── requirements.txt
└── README.md
```

## Data Model

| Dataset | Grain | Purpose |
| --- | --- | --- |
| `dim_province.csv` | One row per province | Province identifier, name, and coordinates |
| `fact_weather_hourly.csv` | One row per province and forecast hour | Weather values and rolling rainfall |
| `fact_risk_hourly.csv` | One row per province and forecast hour | Prototype risk scores and levels |
| `risk_snapshot.csv` | One row per province | Peak-risk forecast and attention flag |

Fact datasets join on `province_code` and `forecast_time`. Facts join to the province dimension on `province_code`.

## Prototype Risk Scoring

All thresholds are project configuration values, not official Vietnamese warning criteria.

| Score | Level |
| ---: | --- |
| 0 | Low |
| 1 | Moderate |
| 2 | High |
| 3 | Extreme |

### Rain risk

| Level | Hourly rainfall |
| --- | ---: |
| Moderate | 5 mm |
| High | 15 mm |
| Extreme | 30 mm |

### Storm risk

Storm risk uses the highest score from hourly rainfall, wind gusts, and thunderstorm weather codes `95`, `96`, and `99`.

| Level | Wind gust |
| --- | ---: |
| Moderate | 40 km/h |
| High | 65 km/h |
| Extreme | 90 km/h |

### Flood indicator

| Level | Six-hour rain | 24-hour rain |
| --- | ---: | ---: |
| Moderate | 25 mm | 50 mm |
| High | 50 mm | 100 mm |
| Extreme | 90 mm | 200 mm |

Combined risk is the highest of the rain, storm, and flood scores.

## Data Quality Checks

The pipeline validates required columns, timestamps, numeric weather values, per-province rolling rainfall, unique province codes, valid coordinates, and exactly 34 province records in the final snapshot.

## Limitations

- CSV storage does not provide transactions, indexing, concurrency control, or strong schema enforcement.
- Each province is represented by one monitoring coordinate.
- Flood indicators exclude river levels, terrain, soil moisture, tides, drainage, and historical flood extent.
- The project does not ingest official Vietnamese warnings.
- Pipeline orchestration is manual.

These limitations motivated Version 2, which moves the project to PostgreSQL, dbt, Airflow, and Docker.

## Documentation

For the expanded walkthrough, see the [Version 1 Wiki](https://github.com/AnTran289/StormWatch-Vietnam/wiki/%F0%9F%93%96-Version-1-(CSV-Pipeline)).

## Author

**An Tran**
Data Engineering Portfolio Project
