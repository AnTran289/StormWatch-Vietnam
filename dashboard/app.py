"""
File: dashboard/app.py

Purpose:
--------
Display StormWatch Vietnam's province-level weather-risk forecast.

Data sources:
-------------
1. analytics_marts.province_risk_snapshot
2. analytics_marts.fact_risk_scores
3. metadata.pipeline_runs

Run:
----
python -m streamlit run dashboard/app.py
"""

# os provides access to database configuration environment variables.
import os

# pandas provides DataFrame transformation functions.
import pandas as pd

# SQLAlchemy manages the PostgreSQL connection pool and SQL statements.
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL

# Streamlit provides dashboard components and caching.
import streamlit as st
import unicodedata
import altair as alt


# ============================================================
# Page configuration
# ============================================================

# This should be the first Streamlit command in the application.
st.set_page_config(
    page_title="StormWatch Vietnam",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Database connection
# ============================================================

@st.cache_resource
def get_database_engine() -> Engine:
    """
    Create one SQLAlchemy engine from the standard DB_* environment variables.
    """
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise RuntimeError("DB_PASSWORD environment variable is required.")

    try:
        port = int(os.getenv("DB_PORT", "5432"))
    except ValueError as error:
        raise RuntimeError("DB_PORT must be an integer.") from error

    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER", "stormwatch_user"),
        password=password,
        host=os.getenv("DB_HOST", "localhost"),
        port=port,
        database=os.getenv("DB_NAME", "stormwatch"),
    )

    return create_engine(database_url, pool_pre_ping=True)


try:
    database_engine = get_database_engine()
except Exception as error:
    st.error("Database connection setup failed. Check the DB_* environment variables.")
    st.exception(error)
    st.stop()


def run_query(
    query: str,
    params: dict | None = None,
) -> pd.DataFrame:
    """
    Execute a read-only query through SQLAlchemy.
    """
    with database_engine.connect() as connection:
        return pd.read_sql_query(
            text(query),
            connection,
            params=params,
        )


# ============================================================
# Database queries
# ============================================================

@st.cache_data(ttl=300)
def load_province_snapshot() -> pd.DataFrame:
    """
    Load the highest forecast-risk hour for every province.

    ttl=300 caches the returned DataFrame for five minutes.

    This prevents every filter interaction from sending another
    identical query to PostgreSQL.
    """

    query = """
        SELECT
            location_id,
            province_code,
            province_name,
            latitude,
            longitude,
            peak_risk_time,
            ingested_at,
            temperature_c,
            relative_humidity_percent,
            precipitation_mm,
            rain_mm,
            rain_6h_mm,
            rain_24h_mm,
            wind_speed_kmh,
            wind_gusts_kmh,
            surface_pressure_hpa,
            weather_code,
            rain_risk_score,
            rain_risk_level,
            storm_risk_score,
            storm_risk_level,
            flood_risk_score,
            flood_risk_level,
            peak_risk_score,
            peak_risk_level,
            requires_attention
        FROM analytics_marts.province_risk_snapshot
        ORDER BY
            peak_risk_score DESC,
            province_name ASC
    """

    return run_query(query)


@st.cache_data(ttl=300)
def load_pipeline_runs() -> pd.DataFrame:
    """
    Load recent pipeline execution records.
    """

    query = """
        SELECT
            run_id,
            pipeline_name,
            started_at,
            completed_at,
            status,
            rows_extracted,
            rows_loaded,
            error_message
        FROM metadata.pipeline_runs
        ORDER BY started_at DESC
        LIMIT 10
    """

    return run_query(query)


@st.cache_data(ttl=300)
def load_province_forecast(
    location_id: int,
) -> pd.DataFrame:
    """
    Load all hourly risk forecasts for one selected province.

    Parameters
    ----------
    location_id:
        Internal PostgreSQL location identifier.
    """

    query = """
        SELECT
            forecast_time,
            temperature_c,
            relative_humidity_percent,
            rain_mm,
            rain_6h_mm,
            rain_24h_mm,
            wind_speed_kmh,
            wind_gusts_kmh,
            surface_pressure_hpa,
            weather_code,
            rain_risk_score,
            storm_risk_score,
            flood_risk_score,
            disaster_risk_score,
            disaster_risk_level
        FROM analytics_marts.fact_risk_scores
        WHERE location_id = :location_id
        ORDER BY forecast_time
    """

    # :location_id is a named SQL parameter.
    #
    # params supplies its value separately, avoiding unsafe
    # SQL string construction.
    return run_query(
        query,
        params={
            "location_id": int(location_id),
        },
    )


# ============================================================
# Helper functions
# ============================================================

def risk_icon(risk_level: str) -> str:
    """
    Return a visual icon for a risk level.
    """
    icons = {
        "Low": "🟢",
        "Moderate": "🟡",
        "High": "🟠",
        "Extreme": "🔴",
    }
    return icons.get(risk_level, "⚪")


MAP_MARKER_ALPHA = 110  # 0=fully transparent, 255=fully opaque


def risk_color_rgba(risk_level: str) -> list[int]:
    """
    Return map marker color by risk level with transparency.
    """
    colors = {
        "Low": [46, 204, 113, MAP_MARKER_ALPHA],
        "Moderate": [241, 196, 15, MAP_MARKER_ALPHA],
        "High": [230, 126, 34, MAP_MARKER_ALPHA],
        "Extreme": [231, 76, 60, MAP_MARKER_ALPHA],
    }
    return colors.get(
        risk_level,
        [149, 165, 166, MAP_MARKER_ALPHA],
    )


def risk_priority(risk_level: str) -> int:
    """
    Convert a risk-level label into a sortable priority.
    """

    priorities = {
        "Low": 0,
        "Moderate": 1,
        "High": 2,
        "Extreme": 3,
    }

    return priorities.get(risk_level, -1)


def format_datetime_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert timestamp columns into pandas datetime values.
    """

    result = dataframe.copy()

    datetime_columns = [
        "peak_risk_time",
        "forecast_time",
        "ingested_at",
        "started_at",
        "completed_at",
    ]

    for column in datetime_columns:
        if column in result.columns:
            result[column] = pd.to_datetime(
                result[column],
                utc=True,
                errors="coerce",
            )

    return result


def normalize_risk_level(value) -> str | None:
    if pd.isna(value):
        return None

    text = str(value).strip().lower()
    mapping = {
        "low": "Low",
        "moderate": "Moderate",
        "high": "High",
        "extreme": "Extreme",
    }
    return mapping.get(text, str(value).strip().title())


def normalize_risk_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    risk_columns = [
        "rain_risk_level",
        "storm_risk_level",
        "flood_risk_level",
        "peak_risk_level",
        "disaster_risk_level",
    ]

    for column in risk_columns:
        if column in result.columns:
            result[column] = result[column].apply(
                normalize_risk_level
            )

    return result


def normalize_text_for_search(value: str) -> str:
    """
    Normalize text for accent-insensitive province search.
    Example: 'Hà Nội' -> 'ha noi'
    """
    if value is None:
        return ""

    text = str(value).strip().casefold()
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        ch for ch in text
        if unicodedata.category(ch) != "Mn"
    )
    # Vietnamese đ/Đ is a separate letter rather than a combining
    # diacritic, so NFD normalization does not convert it to d.
    text = text.replace("đ", "d")
    return " ".join(text.split())


def validate_snapshot(
    snapshot_df: pd.DataFrame,
) -> None:
    """
    Validate the dashboard's primary dataset.
    """

    required_columns = {
        "location_id",
        "province_code",
        "province_name",
        "latitude",
        "longitude",
        "peak_risk_time",
        "peak_risk_score",
        "peak_risk_level",
    }

    missing_columns = (
        required_columns
        - set(snapshot_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Province snapshot is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    if snapshot_df.empty:
        raise ValueError(
            "The province snapshot contains no records."
        )

    province_count = snapshot_df[
        "province_code"
    ].nunique()

    if province_count != 34:
        raise ValueError(
            f"Expected 34 provinces, but found "
            f"{province_count}."
        )


# ============================================================
# Load dashboard data
# ============================================================

try:
    snapshot_df = load_province_snapshot()
    pipeline_runs_df = load_pipeline_runs()

    snapshot_df = format_datetime_columns(
        snapshot_df
    )
    snapshot_df = normalize_risk_columns(
        snapshot_df
    )

    pipeline_runs_df = format_datetime_columns(
        pipeline_runs_df
    )

    validate_snapshot(snapshot_df)

except Exception as error:
    st.error(
        "The dashboard could not load data from PostgreSQL."
    )

    # st.exception() displays the error and traceback.
    # This is useful during development.
    st.exception(error)

    st.stop()


# ============================================================
# Dashboard header
# ============================================================

st.title("🌧️ StormWatch Vietnam")

st.caption(
    "Seven-day prototype storm, rainfall and flood-risk "
    "monitoring across Vietnam's 34 provincial-level units."
)

st.warning(
    "This system contains experimental portfolio-project risk "
    "indicators. It is not an official disaster-warning service."
)


# ============================================================
# Refresh controls
# ============================================================

refresh_column, timestamp_column = st.columns(
    [1, 4]
)

with refresh_column:
    # Clicking this button clears cached query results.
    if st.button(
        "↻ Refresh data",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.rerun()

with timestamp_column:
    latest_ingestion_time = (
        snapshot_df["ingested_at"].max()
    )

    if pd.notna(latest_ingestion_time):
        st.info(
            "Latest forecast ingestion: "
            f"{latest_ingestion_time:%Y-%m-%d %H:%M UTC}"
        )


# ============================================================
# Sidebar filters
# ============================================================

st.sidebar.header("Dashboard Filters")

risk_order = [
    "Low",
    "Moderate",
    "High",
    "Extreme",
]

selected_risks = st.sidebar.multiselect(
    label="Peak risk levels",
    options=risk_order,
    default=risk_order,
)

province_search = st.sidebar.text_input(
    label="Search province",
    placeholder="Example: Hà Nội",
)

attention_only = st.sidebar.checkbox(
    label="Show only provinces requiring attention",
    value=False,
)

filtered_df = snapshot_df[
    snapshot_df["peak_risk_level"].isin(
        selected_risks
    )
].copy()

if province_search:
    search_value = normalize_text_for_search(
        province_search
    )

    filtered_df = filtered_df[
        filtered_df["province_name"]
        .fillna("")
        .apply(normalize_text_for_search)
        .str.contains(
            search_value,
            regex=False,   # treat input as plain text
            na=False,
        )
    ]

if attention_only:
    filtered_df = filtered_df[
        filtered_df["requires_attention"] == True
    ]

st.sidebar.caption(
    f"{filtered_df['province_code'].nunique()} provinces match"
)


# ============================================================
# National summary metrics
# ============================================================

st.subheader("National Overview")

total_provinces = snapshot_df[
    "province_code"
].nunique()

attention_count = snapshot_df[
    snapshot_df["requires_attention"] == True
]["province_code"].nunique()

high_count = snapshot_df[
    snapshot_df["peak_risk_level"] == "High"
]["province_code"].nunique()

extreme_count = snapshot_df[
    snapshot_df["peak_risk_level"] == "Extreme"
]["province_code"].nunique()

highest_risk_row = (
    snapshot_df
    .assign(
        risk_priority=snapshot_df[
            "peak_risk_level"
        ].apply(risk_priority)
    )
    .sort_values(
        by=[
            "risk_priority",
            "peak_risk_score",
        ],
        ascending=[
            False,
            False,
        ],
    )
    .iloc[0]
)

metric_1, metric_2, metric_3, metric_4, metric_5 = (
    st.columns(5)
)

with metric_1:
    st.metric(
        label="Provinces monitored",
        value=total_provinces,
    )

with metric_2:
    st.metric(
        label="Require attention",
        value=attention_count,
    )

with metric_3:
    st.metric(
        label="High risk",
        value=high_count,
    )

with metric_4:
    st.metric(
        label="Extreme risk",
        value=extreme_count,
    )

with metric_5:
    highest_level = highest_risk_row[
        "peak_risk_level"
    ]

    st.metric(
        label="Highest national risk",
        value=(
            f"{risk_icon(highest_level)} "
            f"{highest_level}"
        ),
    )


# ============================================================
# National map and risk distribution
# ============================================================

map_column, chart_column = st.columns(
    [2, 1]
)

with map_column:
    st.subheader("Province Monitoring Map")

    map_df = filtered_df.dropna(
        subset=[
            "latitude",
            "longitude",
        ]
    ).copy()

    if map_df.empty:
        st.info(
            "No provinces match the selected filters."
        )

    else:
        # Add size and color fields for map markers.
        map_df["marker_size"] = (
            map_df["peak_risk_score"]
            .fillna(0)
            .astype(float)
            .add(1)
            .multiply(10000)
        )

        map_df["marker_color"] = map_df[
            "peak_risk_level"
        ].apply(risk_color_rgba)

        st.map(
            map_df,
            latitude="latitude",
            longitude="longitude",
            size="marker_size",
            color="marker_color",
            use_container_width=True,
        )

with chart_column:
    st.subheader("Risk Distribution")

    risk_distribution = (
        filtered_df["peak_risk_level"]
        .value_counts()
        .reindex(
            risk_order,
            fill_value=0,
        )
        .rename("province_count")
    )

    st.bar_chart(
        risk_distribution,
        x_label="Risk level",
        y_label="Province count",
        use_container_width=True,
    )


# ============================================================
# Priority province table
# ============================================================

st.subheader("Priority Provinces")

priority_df = filtered_df[
    filtered_df["requires_attention"] == True
].copy()

priority_df["status"] = (
    priority_df["peak_risk_level"]
    .apply(risk_icon)
)

priority_df = priority_df.sort_values(
    by=[
        "peak_risk_score",
        "peak_risk_time",
    ],
    ascending=[
        False,
        True,
    ],
)

priority_columns = [
    "status",
    "province_name",
    "peak_risk_time",
    "peak_risk_level",
    "rain_6h_mm",
    "rain_24h_mm",
    "wind_gusts_kmh",
    "storm_risk_level",
    "flood_risk_level",
]

if priority_df.empty:
    st.success(
        "No provinces currently have High or Extreme "
        "prototype risk levels."
    )

else:
    st.dataframe(
        priority_df[priority_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "status": st.column_config.TextColumn(
                "Status"
            ),
            "province_name": st.column_config.TextColumn(
                "Province"
            ),
            "peak_risk_time": (
                st.column_config.DatetimeColumn(
                    "Peak risk time",
                    format="YYYY-MM-DD HH:mm",
                    timezone="Asia/Ho_Chi_Minh",
                )
            ),
            "peak_risk_level": (
                st.column_config.TextColumn(
                    "Peak risk"
                )
            ),
            "rain_6h_mm": (
                st.column_config.NumberColumn(
                    "Rain 6h",
                    format="%.1f mm",
                )
            ),
            "rain_24h_mm": (
                st.column_config.NumberColumn(
                    "Rain 24h",
                    format="%.1f mm",
                )
            ),
            "wind_gusts_kmh": (
                st.column_config.NumberColumn(
                    "Wind gust",
                    format="%.1f km/h",
                )
            ),
        },
    )


# ============================================================
# Province drilldown
# ============================================================

st.subheader("Province Forecast Drilldown")

province_options = (
    snapshot_df[
        [
            "location_id",
            "province_name",
        ]
    ]
    .sort_values("province_name")
    .drop_duplicates()
)

province_name_to_id = dict(
    zip(
        province_options["province_name"],
        province_options["location_id"],
    )
)

selected_province_name = st.selectbox(
    label="Select a province",
    options=list(
        province_name_to_id.keys()
    ),
)

selected_location_id = province_name_to_id[
    selected_province_name
]

try:
    province_forecast_df = load_province_forecast(
        location_id=int(
            selected_location_id
        )
    )

    province_forecast_df = (
        format_datetime_columns(
            province_forecast_df
        )
    )
    province_forecast_df = normalize_risk_columns(
        province_forecast_df
    )

except Exception as error:
    st.error(
        "Could not load the selected province forecast."
    )
    st.exception(error)
    st.stop()


selected_snapshot = snapshot_df[
    snapshot_df["location_id"]
    == selected_location_id
].iloc[0]

detail_1, detail_2, detail_3, detail_4 = st.columns(
    4
)

with detail_1:
    st.metric(
        label="Peak risk",
        value=(
            f"{risk_icon(selected_snapshot['peak_risk_level'])} "
            f"{selected_snapshot['peak_risk_level']}"
        ),
    )

with detail_2:
    st.metric(
        label="Peak 24h rainfall",
        value=(
            f"{selected_snapshot['rain_24h_mm']:.1f} mm"
        ),
    )

with detail_3:
    st.metric(
        label="Peak wind gust",
        value=(
            f"{selected_snapshot['wind_gusts_kmh']:.1f} km/h"
        ),
    )

with detail_4:
    st.metric(
        label="Peak risk score",
        value=int(
            selected_snapshot["peak_risk_score"]
        ),
    )


# ============================================================
# Province forecast charts
# ============================================================

rain_chart_df = (
    province_forecast_df
    .set_index("forecast_time")
    [
        [
            "rain_mm",
            "rain_6h_mm",
            "rain_24h_mm",
        ]
    ]
)

st.markdown("#### Rainfall Forecast")

st.line_chart(
    rain_chart_df,
    x_label="Forecast time",
    y_label="Rainfall (mm)",
    use_container_width=True,
)

wind_chart_df = (
    province_forecast_df
    .set_index("forecast_time")
    [
        [
            "wind_speed_kmh",
            "wind_gusts_kmh",
        ]
    ]
)

st.markdown("#### Wind Forecast")

st.line_chart(
    wind_chart_df,
    x_label="Forecast time",
    y_label="Wind speed (km/h)",
    use_container_width=True,
)

risk_chart_df = (
    province_forecast_df
    .set_index("forecast_time")
    [
        [
            "rain_risk_score",
            "storm_risk_score",
            "flood_risk_score",
            "disaster_risk_score",
        ]
    ]
)

st.markdown("#### Prototype Risk Scores")

st.line_chart(
    risk_chart_df,
    x_label="Forecast time",
    y_label="Risk score",
    use_container_width=True,
)


# ============================================================
# Complete province table
# ============================================================

st.subheader("All Province Snapshot Records")

filtered_df["status"] = (
    filtered_df["peak_risk_level"]
    .apply(risk_icon)
)

all_province_columns = [
    "status",
    "province_code",
    "province_name",
    "peak_risk_time",
    "peak_risk_score",
    "peak_risk_level",
    "rain_24h_mm",
    "wind_gusts_kmh",
    "storm_risk_level",
    "flood_risk_level",
    "requires_attention",
]

st.dataframe(
    filtered_df[all_province_columns],
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# Pipeline health
# ============================================================

st.subheader("Pipeline Health")

if pipeline_runs_df.empty:
    st.info(
        "No pipeline-run metadata is available."
    )

else:
    latest_run = pipeline_runs_df.iloc[0]

    run_metric_1, run_metric_2, run_metric_3 = (
        st.columns(3)
    )

    with run_metric_1:
        st.metric(
            label="Latest pipeline status",
            value=str(
                latest_run["status"]
            ).upper(),
        )

    with run_metric_2:
        st.metric(
            label="Rows extracted",
            value=int(
                latest_run["rows_extracted"]
                or 0
            ),
        )

    with run_metric_3:
        st.metric(
            label="Rows loaded",
            value=int(
                latest_run["rows_loaded"]
                or 0
            ),
        )

    pipeline_display_columns = [
        "run_id",
        "pipeline_name",
        "started_at",
        "completed_at",
        "status",
        "rows_extracted",
        "rows_loaded",
        "error_message",
    ]

    st.dataframe(
        pipeline_runs_df[
            pipeline_display_columns
        ],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# Data explanation
# ============================================================

with st.expander("About the dashboard"):
    st.markdown(
        """
        **Data pipeline**

        1. Python fetches forecast data from Open-Meteo.
        2. Raw responses are preserved as JSON.
        3. Hourly records are loaded into PostgreSQL.
        4. dbt selects the latest forecast version.
        5. dbt calculates rolling rainfall and prototype risks.
        6. Streamlit queries the dbt marts directly.

        **Important limitation**

        Flood risk currently uses forecast rainfall accumulation.
        It does not yet include official river-gauge readings,
        soil moisture, drainage capacity, terrain or official
        Vietnamese emergency-warning information.
        """
    )
