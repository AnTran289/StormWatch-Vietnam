"""
Display the 7-day peak disaster risk for Vietnam's
34 provincial-level administrative units.

Input: data/processed/risk_snapshot.csv
Run with: python -m streamlit run dashboard/app.py
"""

from pathlib import Path
import unicodedata
import pandas as pd
import pydeck as pdk
import streamlit as st

# ============================================================
# Page configuration
# ============================================================

# Set the page title and icon
st.set_page_config(
    page_title = "FloodAid - StormWatch Vietnam",
    page_icon = "🌧️",
    layout = "wide",
)

# ============================================================
# File configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "risk_snapshot.csv"
WEATHER_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "fact_weather_hourly.csv"
RISK_LEVELS = ["Low", "Moderate", "High", "Extreme"]

# ============================================================
# Data loading
# ============================================================

@st.cache_data # stores data temporarily -> Streamlit doesn't need to read CSV again

# Read and prepare the risk snapshot
def load_snapshot(file_mtime: float)->pd.DataFrame:

    # Check if the input file exists
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {DATA_PATH}")
    
    # Read the CSV file into a pandas DataFrame
    snapshot_df = pd.read_csv(DATA_PATH, dtype={"province_code": str}) # Keep province_code as text bc it is an identifier

    # Convert peak_risk_time to datetime 
    if "peak_risk_time" in snapshot_df.columns:
        snapshot_df["peak_risk_time"] = pd.to_datetime(snapshot_df["peak_risk_time"], errors="coerce")

    # Convert coordinates to numeric, coercing errors to NaN
    for col in ["latitude", "longitude"]:
        if col in snapshot_df.columns:
            snapshot_df[col] = pd.to_numeric(snapshot_df[col], errors="coerce")

    return snapshot_df


@st.cache_data
def load_weather_forecast(file_mtime: float) -> pd.DataFrame:

    if not WEATHER_DATA_PATH.exists():
        raise FileNotFoundError(f"Weather forecast file not found: {WEATHER_DATA_PATH}")

    weather_df = pd.read_csv(WEATHER_DATA_PATH, dtype={"province_code": str})

    for col in ["forecast_time", "ingested_at"]:
        if col in weather_df.columns:
            weather_df[col] = pd.to_datetime(weather_df[col], errors="coerce")

    return weather_df

# ============================================================
# Helper functions
# ============================================================

# Return an icon for each risk level to display in the Streamlit app
def get_risk_icon(risk_level: str)->str:
    risk_icons = {
        "Low": "🟢",
        "Moderate": "🟡",
        "High": "🟠",
        "Extreme": "🔴",
    }
    return risk_icons.get(risk_level, "⚪")


def get_risk_color(risk_level: str) -> list[int]:
    risk_colors = {
        "Low": [46, 204, 113, 200],
        "Moderate": [241, 196, 15, 210],
        "High": [230, 126, 34, 220],
        "Extreme": [231, 76, 60, 230],
    }
    return risk_colors.get(risk_level, [149, 165, 166, 180])


def get_marker_radius(risk_level: str) -> int:
    marker_radius = {
        "Low": 18000,
        "Moderate": 22000,
        "High": 26000,
        "Extreme": 30000,
    }
    return marker_radius.get(risk_level, 18000)

# Return the highest overall risk level
def get_highest_risk_level(snapshot_df: pd.DataFrame)->str:
    
    # Map risk levels to numeric values for comparison
    priority_map = {
        "Low": 0,
        "Moderate": 1,
        "High": 2,
        "Extreme": 3,}
    
    # Convert each risk level to its corresponding numeric value
    priority_values = snapshot_df["peak_risk_level"].map(priority_map).fillna(0)

    # returns the index with the highest numeric value
    highest_priority = priority_values.idxmax()

    # Use that index to return the corresponding risk label
    return snapshot_df.loc[highest_priority, "peak_risk_level"]


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(without_accents.lower().split())

# ============================================================
# Load data
# ============================================================

try:
    snapshot_df = load_snapshot(DATA_PATH.stat().st_mtime)
except FileNotFoundError as e:
    st.error(f"Error: {e}")
    st.stop()  # Stop execution if the file is not found

try:
    weather_df = load_weather_forecast(WEATHER_DATA_PATH.stat().st_mtime)
except FileNotFoundError as e:
    st.warning(f"Weather forecast details unavailable: {e}")
    weather_df = pd.DataFrame()

# ============================================================
# Dashboard header
# ============================================================

st.title("Stormwatch Vietnam 🌧️")

st.caption("A 7-day peak disaster risk snapshot for Vietnam's 34 provincial-level administrative units.")

st.warning("⚠️ This dashboard is for demonstration purposes only. It does not provide real-time disaster alerts. Please refer to official sources for emergency information.")

# ============================================================
# Sidebar filters
# ============================================================

st.sidebar.header("Dashboard Filters")

# Show all supported risk levels, even if some are not present in current data.
risk_levels = RISK_LEVELS

# multi-select filter for risk levels
selected_risk_levels = st.sidebar.multiselect(
    label = "Select Risk Levels",
    options = risk_levels,
    default = risk_levels, # default to all risk levels selected
)

# Filter the DataFrame based on user's selection
filtered_df = snapshot_df[snapshot_df["peak_risk_level"].isin(selected_risk_levels)].copy()  # Create a copy to avoid SettingWithCopyWarning

# Let user search for a province
province_search = st.sidebar.text_input(
    label = "Search Province",
    placeholder = "Enter province name...",
)

# Apply the province search filter if the user has entered a search term
if province_search:
    search_value = normalize_text(province_search)
    province_name_norm = filtered_df["province_name"].map(normalize_text)
    province_code_norm = filtered_df["province_code"].fillna("").astype(str).str.lower()
    filtered_df = filtered_df[
        province_name_norm.str.contains(search_value, regex=False, na=False)
        | province_code_norm.str.contains(search_value, regex=False, na=False)
    ]

filtered_risk_distribution = (
    filtered_df["peak_risk_level"]
    .value_counts()
    .reindex(RISK_LEVELS, fill_value=0)
)

# ============================================================
# Summary metrics
# ============================================================

# Count the total number of provinces in the full snapshot
total_provinces = snapshot_df["province_code"].nunique()

# Count provinces with High or Extreme risk levels in the filtered DataFrame
attention_count = filtered_df[filtered_df["peak_risk_level"].isin(["High", "Extreme"])]["province_code"].nunique()

# Count Extreme-risk provinces
extreme_count = filtered_df[filtered_df["peak_risk_level"] == "Extreme"]["province_code"].nunique()

# Find the highest national risk level
highest_risk_level = get_highest_risk_level(snapshot_df)


# Create 4 side-by-side dashboard areas.
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

# Displats metrics in the dashboard
with metric_col1:
    st.metric(
        label = "Provinces monitored",
        value = total_provinces,
    )

with metric_col2:
    st.metric(
        label = "Provinces needing attention",
        value = attention_count,
    )

with metric_col3:
    st.metric(
        label = "Extreme-risk provinces",
        value = extreme_count,
    )

with metric_col4:
    st.metric(
        label = "Highest national risk level",
        value = highest_risk_level,
        delta = get_risk_icon(highest_risk_level),
    )

# ============================================================
# Map section
# ============================================================

st.subheader("National Risk Map")

# Remove rows with missing coordinates to avoid errors in the map display
map_df = filtered_df.dropna(subset=["latitude", "longitude"]).copy()

if map_df.empty:
    st.warning("No provinces match the selected filters. Please adjust your filters to view the map.")
else:
    map_df["risk_color"] = map_df["peak_risk_level"].apply(get_risk_color)
    map_df["marker_radius"] = map_df["peak_risk_level"].apply(get_marker_radius)
    map_df["peak_risk_time_label"] = map_df["peak_risk_time"].dt.strftime("%Y-%m-%d %H:%M")
    map_df["peak_risk_time_label"] = map_df["peak_risk_time_label"].fillna("Unknown")

    st.caption(
        "Map colors: "
        + " | ".join(
            f"{get_risk_icon(level)} {level}: {int(filtered_risk_distribution[level])}"
            for level in RISK_LEVELS
        )
    )

    # Plot each province as a point on an interactive map, colored by risk level.
    risk_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[longitude, latitude]",
        get_fill_color="risk_color",
        get_radius="marker_radius",
        get_line_color=[68, 68, 68, 180],
        line_width_min_pixels=1,
        pickable=True,
        stroked=True,
    )

    risk_view = pdk.ViewState(
        latitude=float(map_df["latitude"].mean()),
        longitude=float(map_df["longitude"].mean()),
        zoom=4.6,
        pitch=0,
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[risk_layer],
            initial_view_state=risk_view,
            tooltip={
                "html": "<b>{province_name}</b><br/>Risk: {peak_risk_level}<br/>Peak time: {peak_risk_time_label}",
                "style": {"backgroundColor": "#1f2937", "color": "white"},
            },
        ),
        use_container_width=True,
    )

# ============================================================
# Risk distribution
# ============================================================

st.subheader("Risk Distribution")

# Count provinces in each risk category for the filtered DataFrame
risk_distribution = filtered_risk_distribution

# Creates interative bar chart
st.bar_chart(
    risk_distribution,
    x_label = "Risk Level",
    y_label = "Number of Provinces",
)

# ============================================================
# Provinces requiring attention
# ============================================================

st.subheader("Priority Provinces")

# Keep only high and extreme risk provinces for the table
priority_df = filtered_df[filtered_df["peak_risk_level"].isin(["High", "Extreme"])].copy()

# Sort the most urgent provinces first.
priority_df = priority_df.sort_values(
    by=["alert_priority", "peak_risk_score", "peak_risk_time"],
    ascending=[False, False, True],
)

if priority_df.empty:
    st.success("No provinces currently have High or Extreme "
               "risk levels. Please check back later for updates.")
    
else:

    # Add visual status column.
    priority_df["status"] = priority_df["peak_risk_level"].apply(get_risk_icon)

    # Choose columns to display in the priority table
    priority_columns = [
        "status",
        "province_name",
        "peak_risk_time",
        "peak_risk_level",
        "rain_24h",
        "wind_gust_rate",
        "storm_risk_level",
        "flood_risk_level",
    ]

    # Keep only the columns that exist in the DataFrame
    priority_columns = [col for col in priority_columns if col in priority_df.columns]

    # display interactive table
    st.dataframe(
        priority_df[priority_columns],
        use_container_width=True,
        hide_index=True,
    )

# ============================================================
# Complete province table
# ============================================================

st.subheader("All Provinces Risk Records")

# Add an icon to each province
filtered_df["status"] = filtered_df["peak_risk_level"].apply(get_risk_icon)

# Select useful columns to display in the complete table
display_columns = [
    "status",
    "province_name",
    "province_code",
    "peak_risk_time",
    "peak_risk_level",
    "peak_score",
    "rain_24h",
    "wind_gust_rate",
    "storm_risk_level",
    "flood_risk_level",
    "requires_attention",
]

# keep only the columns that exist in the DataFrame
display_columns = [col for col in display_columns if col in filtered_df.columns]

st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
    hide_index=True,
)

# ============================================================
# Weather forecast details
# ============================================================

st.subheader("Weather Forecast Details")

if weather_df.empty:
    st.info("Weather forecast details are not available right now.")
else:
    province_lookup = (
        snapshot_df[["province_code", "province_name"]]
        .drop_duplicates(subset=["province_code"])
    )

    weather_forecast_df = weather_df.merge(
        province_lookup,
        on="province_code",
        how="left",
    )

    weather_forecast_df = weather_forecast_df[
        weather_forecast_df["province_code"].isin(filtered_df["province_code"].unique())
    ].copy()

    if province_search:
        province_name_norm = weather_forecast_df["province_name"].map(normalize_text)
        province_code_norm = weather_forecast_df["province_code"].fillna("").astype(str).str.lower()
        search_value = normalize_text(province_search)
        weather_forecast_df = weather_forecast_df[
            province_name_norm.str.contains(search_value, regex=False, na=False)
            | province_code_norm.str.contains(search_value, regex=False, na=False)
        ]

    weather_display_columns = [
        "province_name",
        "forecast_time",
        "temperature_c",
        "humidity_percent",
        "rain_mm",
        "rain_6h_mm",
        "rain_24h_mm",
        "wind_speed_kmh",
        "wind_gust_kmh",
        "surface_pressure_hpa",
        "weather_code",
    ]

    weather_display_columns = [
        col for col in weather_display_columns if col in weather_forecast_df.columns
    ]

    weather_forecast_df = weather_forecast_df.sort_values(
        by=["province_name", "forecast_time"],
        ascending=[True, True],
    )

    st.caption(
        "Hourly forecast rows for provinces that match the current risk and province filters."
    )

    st.dataframe(
        weather_forecast_df[weather_display_columns],
        use_container_width=True,
        hide_index=True,
    )

# ============================================================
# Data information
# ============================================================

# creates a collapsible section to display information
with st.expander("About this data"):
    st.write(
        "Each province is represented by the forecast hour with "
        "its highest combined prototype risk score."
    )

    st.write(
        "Weather data is collected from Open-Meteo using the "
        "latitude and longitude stored in dim_locations.csv."
    )

    st.write(
        "Flood risk currently uses forecast rainfall accumulation "
        "only. It does not yet include river levels, elevation, "
        "soil moisture or drainage data."
    )