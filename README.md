# StormWatch Vietnam - Version 1

StormWatch Vietnam is a CSV-based data engineering portfolio project that collects public weather forecast data for Vietnam’s 34 provincial-level administrative units, transforms the data into prototype weather-risk indicators, and presents the results in an interactive Streamlit dashboard.

The project demonstrates an end-to-end batch pipeline using public APIs, Python, pandas, CSV storage, risk-scoring logic, geospatial data, and dashboard visualisation.

> **Disclaimer:** This project is for educational and portfolio purposes only. The generated risk levels are experimental indicators and must not be treated as official disaster warnings, evacuation advice, or emergency-management guidance.

---

## Project Overview

StormWatch Vietnam performs the following workflow:

1. Fetch Vietnam’s 34 current provincial-level administrative units.
2. Enrich the province dataset with latitude and longitude.
3. Call the Open-Meteo API for each province.
4. Preserve raw API responses as JSON.
5. Transform hourly weather forecasts into structured CSV files.
6. Calculate rain, storm, flood, and combined risk indicators.
7. Create one peak-risk record per province.
8. Display the results through a Streamlit dashboard.

---

## Version 1 Architecture

```text
Vietnam Provinces API
        ↓
data/reference/vietnam_34_provinces.csv
        ↓
Coordinate enrichment
        ↓
data/reference/dim_location.csv
        ↓
Open-Meteo Forecast API
        ↓
Raw JSON responses
        ↓
data/processed/weather_hourly.csv
        ↓
Risk calculation
        ↓
data/processed/dim_province.csv
data/processed/fact_weather_hourly.csv
data/processed/fact_risk_hourly.csv
        ↓
Province risk snapshot
        ↓
data/processed/risk_snapshot.csv
        ↓
Streamlit dashboard
```

---

## Main Features

### Province ingestion

The project retrieves Vietnam’s current 34 provincial-level administrative units from a public administrative API.

The output is stored in:

```text
data/reference/vietnam_34_provinces.csv
```

### Coordinate enrichment

Province records are enriched with latitude and longitude so they can be used in weather API requests and displayed on the national monitoring map.

The enriched file is stored in:

```text
data/reference/dim_location.csv
```

### Open-Meteo weather ingestion

The weather ingestion pipeline calls Open-Meteo for each provincial monitoring point and requests a seven-day hourly forecast.

The requested variables include:

* temperature;
* relative humidity;
* precipitation;
* rain;
* wind speed;
* wind gusts;
* surface pressure;
* weather code.

Raw API responses are saved in:

```text
data/raw/open_meteo/
```

The combined hourly forecast dataset is saved in:

```text
data/processed/weather_hourly.csv
```

### Risk calculation

The risk engine calculates four prototype indicators:

* rainfall risk;
* storm risk;
* rainfall-based flood risk;
* combined disaster risk.

The risk engine also produces a small analytical data model:

```text
data/processed/dim_province.csv
data/processed/fact_weather_hourly.csv
data/processed/fact_risk_hourly.csv
```

### Province risk snapshot

The risk snapshot pipeline selects the highest-risk forecast hour for each province.

The final dashboard dataset contains one row per provincial-level unit:

```text
data/processed/risk_snapshot.csv
```

### Streamlit dashboard

The dashboard provides:

* monitoring for all 34 provincial-level units;
* a seven-day peak-risk overview;
* national summary metrics;
* an interactive risk map;
* risk-level filters;
* province search;
* risk-distribution charts;
* High and Extreme priority tables;
* detailed hourly weather forecasts;
* rainfall and wind charts;
* downloadable CSV data.

---

## Technology Stack

| Area                     | Technology                 |
| ------------------------ | -------------------------- |
| Programming language     | Python                     |
| API requests             | Requests                   |
| Data processing          | pandas                     |
| Weather data             | Open-Meteo                 |
| Province data            | Vietnam Provinces Open API |
| Geocoding                | OpenStreetMap Nominatim    |
| Raw storage              | JSON                       |
| Processed storage        | CSV                        |
| Dashboard                | Streamlit                  |
| Geospatial visualisation | PyDeck                     |
| Version control          | Git and GitHub             |

---

## Project Structure

```text
StormWatch-Vietnam/
│
├── dashboard/
│   └── app.py
│
├── data/
│   ├── analytics/
│   │   └── risk_snapshot.csv
│   │
│   ├── processed/
│   │   ├── dim_province.csv
│   │   ├── fact_risk_hourly.csv
│   │   ├── fact_weather_hourly.csv
│   │   ├── risk_snapshot.csv
│   │   └── weather_hourly.csv
│   │
│   ├── raw/
│   │   └── open_meteo/
│   │
│   └── reference/
│       ├── dim_location.csv
│       └── vietnam_34_provinces.csv
│
├── src/
│   ├── ingestion/
│   │   ├── fetch_vietnam_provinces.py
│   │   ├── coordinates_enrich.py
│   │   └── fetch_weather.py
│   │
│   ├── risk_engine/
│   │   └── calculate_risk_scores.py
│   │
│   └── transformation/
│       └── risk_snapshot.py
│
├── requirements.txt
└── README.md
```

Some generated CSV files may differ depending on which pipeline stages have already been executed.

---

## Data Pipeline

### 1. Fetch Vietnam province data

Script:

```text
src/ingestion/fetch_vietnam_provinces.py
```

Purpose:

* call the Vietnam Provinces API;
* retrieve the current 34 provincial-level units;
* transform the JSON response into tabular data;
* save the result as CSV.

Run:

```bash
python src/ingestion/fetch_vietnam_provinces.py
```

Expected output:

```text
data/reference/vietnam_34_provinces.csv
```

---

### 2. Enrich provinces with coordinates

Script:

```text
src/ingestion/coordinates_enrich.py
```

Purpose:

* read the province reference data;
* geocode province names;
* add latitude and longitude;
* save the enriched location dimension.

Run:

```bash
python src/ingestion/coordinates_enrich.py
```

Expected output:

```text
data/reference/dim_location.csv
```

The script should respect the public geocoding service’s usage policy and avoid excessive request frequency.

---

### 3. Fetch Open-Meteo forecasts

Script:

```text
src/ingestion/fetch_weather.py
```

Purpose:

* read province coordinates from `dim_location.csv`;
* request seven-day hourly forecasts from Open-Meteo;
* save each original API response as JSON;
* combine all provincial forecasts into one CSV dataset.

Run:

```bash
python src/ingestion/fetch_weather.py
```

Expected outputs:

```text
data/raw/open_meteo/
data/processed/weather_hourly.csv
```

For 34 provinces and seven forecast days, the output normally contains approximately:

```text
34 × 7 × 24 = 5,712 hourly rows
```

---

### 4. Calculate risk scores

Script:

```text
src/risk_engine/calculate_risk_scores.py
```

Purpose:

* validate the hourly weather dataset;
* normalise weather column names;
* calculate six-hour and 24-hour rolling rainfall totals;
* calculate prototype rain, storm, flood, and combined risk scores;
* produce analytical dimension and fact files.

Run:

```bash
python src/risk_engine/calculate_risk_scores.py
```

Expected outputs:

```text
data/processed/dim_province.csv
data/processed/fact_weather_hourly.csv
data/processed/fact_risk_hourly.csv
```

---

### 5. Create the province risk snapshot

Script:

```text
src/transformation/risk_snapshot.py
```

Purpose:

* read hourly risk records;
* merge province coordinates;
* select the highest-risk forecast hour for each province;
* assign alert priority;
* identify provinces requiring attention;
* validate that the output contains exactly 34 unique provinces.

Run:

```bash
python src/transformation/risk_snapshot.py
```

Expected output:

```text
data/processed/risk_snapshot.csv
```

---

### 6. Run the Streamlit dashboard

Script:

```text
dashboard/app.py
```

The dashboard reads:

```text
data/processed/risk_snapshot.csv
data/processed/fact_weather_hourly.csv
```

Run:

```bash
python -m streamlit run dashboard/app.py
```

The application should open in the browser at:

```text
http://localhost:8501
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/AnTran289/StormWatch-Vietnam.git
cd StormWatch-Vietnam
```

### 2. Create a virtual environment

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

### 3. Upgrade pip

```bash
python -m pip install --upgrade pip
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

If the requirements file is unavailable or incomplete, install the main packages manually:

```bash
python -m pip install pandas requests streamlit pydeck
```

---

## Recommended Execution Order

Run the project from the repository root in this order:

```bash
python src/ingestion/fetch_vietnam_provinces.py
python src/ingestion/coordinates_enrich.py
python src/ingestion/fetch_weather.py
python src/risk_engine/calculate_risk_scores.py
python src/transformation/risk_snapshot.py
python -m streamlit run dashboard/app.py
```

Each script depends on output produced by the previous stage.

---

## Data Model

### Province dimension

```text
data/processed/dim_province.csv
```

Typical columns:

| Column          | Description                   |
| --------------- | ----------------------------- |
| `province_code` | Province identifier           |
| `province_name` | Province or municipality name |
| `latitude`      | Monitoring-point latitude     |
| `longitude`     | Monitoring-point longitude    |

### Weather fact table

```text
data/processed/fact_weather_hourly.csv
```

Typical columns:

| Column                 | Description                       |
| ---------------------- | --------------------------------- |
| `province_code`        | Province identifier               |
| `forecast_time`        | Hourly forecast timestamp         |
| `ingested_at`          | Time the data was collected       |
| `temperature_c`        | Temperature in Celsius            |
| `humidity_percent`     | Relative humidity                 |
| `rain_mm`              | Hourly rainfall                   |
| `rain_6h_mm`           | Rolling six-hour rainfall         |
| `rain_24h_mm`          | Rolling 24-hour rainfall          |
| `wind_speed_kmh`       | Wind speed                        |
| `wind_gust_kmh`        | Wind-gust speed                   |
| `surface_pressure_hpa` | Surface pressure                  |
| `weather_code`         | Open-Meteo weather condition code |

### Risk fact table

```text
data/processed/fact_risk_hourly.csv
```

Typical columns:

| Column                | Description                 |
| --------------------- | --------------------------- |
| `province_code`       | Province identifier         |
| `forecast_time`       | Forecast timestamp          |
| `rain_score`          | Rain risk score             |
| `rain_risk_level`     | Rain risk category          |
| `storm_score`         | Storm risk score            |
| `storm_risk_level`    | Storm risk category         |
| `flood_score`         | Rainfall-based flood score  |
| `flood_risk_level`    | Flood risk category         |
| `combined_score`      | Highest combined risk score |
| `combined_risk_level` | Overall risk category       |

### Province snapshot

```text
data/processed/risk_snapshot.csv
```

Typical columns:

| Column               | Description                |
| -------------------- | -------------------------- |
| `province_code`      | Province identifier        |
| `province_name`      | Province name              |
| `latitude`           | Monitoring latitude        |
| `longitude`          | Monitoring longitude       |
| `peak_risk_time`     | Highest-risk forecast time |
| `peak_risk_score`    | Highest combined score     |
| `peak_risk_level`    | Highest risk category      |
| `alert_priority`     | Numeric priority           |
| `requires_attention` | High or Extreme risk flag  |

---

## Risk Scoring

The project uses four prototype levels:

| Score | Level    |
| ----: | -------- |
|     0 | Low      |
|     1 | Moderate |
|     2 | High     |
|     3 | Extreme  |

### Rain risk

Hourly rain thresholds:

| Level    |   Rainfall |
| -------- | ---------: |
| Moderate |  5 mm/hour |
| High     | 15 mm/hour |
| Extreme  | 30 mm/hour |

### Storm risk

Storm risk uses the highest of:

* hourly rain score;
* wind-gust score;
* thunderstorm weather-code score.

Wind-gust thresholds:

| Level    | Wind gust |
| -------- | --------: |
| Moderate |   40 km/h |
| High     |   65 km/h |
| Extreme  |   90 km/h |

Thunderstorm-related Open-Meteo weather codes include:

```text
95, 96, 99
```

### Flood indicator

The first version uses accumulated rainfall only.

Six-hour rainfall thresholds:

| Level    | Rainfall |
| -------- | -------: |
| Moderate |    25 mm |
| High     |    50 mm |
| Extreme  |    90 mm |

24-hour rainfall thresholds:

| Level    | Rainfall |
| -------- | -------: |
| Moderate |    50 mm |
| High     |   100 mm |
| Extreme  |   200 mm |

### Combined risk

The combined risk is the highest value among:

```text
rain score
storm score
flood score
```

These thresholds are project configuration values and are not official Vietnamese warning criteria.

---

## Data Quality Checks

The pipeline includes validation such as:

* exactly 34 unique provincial-level units;
* no duplicate province codes in the snapshot;
* required columns must exist;
* invalid timestamps are removed;
* coordinates must not be missing;
* rainfall and weather values are converted to numeric formats;
* rolling rainfall is calculated separately for each province;
* the final risk snapshot contains one record per province.

Examples:

```python
if len(snapshot_df) != 34:
    raise ValueError("Expected 34 provinces.")

if snapshot_df["province_code"].duplicated().sum() > 0:
    raise ValueError("Duplicate province codes found.")
```

---

## Dashboard Features

### National overview

The dashboard displays:

* total provinces monitored;
* provinces requiring attention;
* Extreme-risk province count;
* highest national risk level.

### Interactive risk map

The PyDeck map uses:

* province latitude and longitude;
* marker colours based on risk level;
* marker size based on risk severity;
* province and peak-risk details in tooltips.

### Risk distribution

A bar chart shows the number of provinces in each category:

```text
Low
Moderate
High
Extreme
```

### Filters

Users can filter by:

* one or more risk levels;
* province name;
* province code.

Search normalisation allows province names to be searched without Vietnamese accents.

### Priority provinces

High and Extreme-risk provinces are displayed in a separate priority table.

### Province drilldown

The dashboard can display hourly forecast information for a selected province using:

```text
data/processed/fact_weather_hourly.csv
```

---

## Engineering Concepts Demonstrated

This Version 1 project demonstrates:

* REST API ingestion;
* combining multiple public data sources;
* geospatial data enrichment;
* batch ETL design;
* raw JSON preservation;
* pandas transformations;
* rolling-window calculations;
* analytical dimension and fact tables;
* data validation;
* aggregation from hourly to province level;
* interactive dashboard development;
* modular Python project organisation.

---

## Current Limitations

### CSV storage

CSV files are suitable for a first prototype but do not provide:

* database transactions;
* concurrency control;
* indexing;
* efficient incremental loading;
* strong schema enforcement;
* scalable queries.

### One coordinate per province

Each provincial-level unit is represented by one monitoring point. Large provinces may contain major weather variation that a single coordinate cannot capture.

### Rainfall-based flood indicator

The flood score currently does not include:

* river-gauge readings;
* river discharge;
* tidal data;
* terrain slope;
* watershed boundaries;
* soil moisture;
* drainage capacity;
* historical flood extent.

### No official alerts

The project does not currently ingest official Vietnamese meteorological or emergency-management warnings.

### Manual orchestration

Version 1 scripts must be executed manually and in the correct sequence.

---

## Planned Version 2

Version 2 upgrades the project from a CSV pipeline to a production-style data platform.

Planned or in-progress improvements include:

* PostgreSQL storage;
* incremental and idempotent loading;
* raw, staging, intermediate, and mart schemas;
* dbt SQL transformations;
* dbt tests and lineage documentation;
* Airflow orchestration;
* Docker Compose;
* pipeline-run metadata;
* Streamlit queries directly from PostgreSQL;
* automated tests with pytest;
* GitHub Actions CI;
* object storage using MinIO or S3-compatible storage;
* cloud deployment.

Target architecture:

```text
Public APIs
    ↓
Python ingestion
    ↓
Raw object storage
    ↓
PostgreSQL
    ↓
dbt transformations
    ↓
Data quality tests
    ↓
Streamlit dashboard
    ↓
Airflow orchestration
    ↓
Docker Compose
    ↓
GitHub Actions
```

---

## Portfolio Purpose

StormWatch Vietnam was created as a data engineering portfolio project to demonstrate practical entry-level skills in:

* Python;
* SQL-oriented data modelling;
* API integration;
* ETL pipelines;
* geospatial enrichment;
* time-series transformation;
* analytical dataset creation;
* risk-scoring logic;
* dashboard integration;
* data validation;
* technical documentation.

The project is designed to evolve from a functional CSV-based prototype into a more production-oriented data platform.

---

## Disclaimer

StormWatch Vietnam is an educational software project.

It must not be used as a substitute for:

* official weather forecasts;
* government disaster warnings;
* evacuation instructions;
* rescue coordination;
* professional flood modelling;
* official emergency-management systems.

For real emergency information, always consult official Vietnamese authorities and recognised meteorological agencies.

---

## Author

**An Tran**

Data Engineering Portfolio Project
