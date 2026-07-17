"""Airflow DAGs for the StormWatch Vietnam data pipelines."""

from datetime import timedelta
import subprocess

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG


PROJECT_DIR = "/opt/airflow/project"
PYTHON = "python"

DEFAULT_ARGS = {
    "owner": "stormwatch",
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}


def mark_run_failed(context) -> None:
    """Persist DAG failures for the dashboard without masking the original error."""
    error = str(context.get("exception") or "Airflow task failed")[:2000]
    subprocess.run(
        [
            PYTHON,
            f"{PROJECT_DIR}/src/warehouse/load_postgres.py",
            "finish",
            "--run-id",
            context["dag_run"].run_id,
            "--status",
            "failed",
            "--error",
            error,
        ],
        cwd=PROJECT_DIR,
        check=False,
    )


with DAG(
    dag_id="stormwatch_weather_pipeline",
    description="Ingest forecasts, load PostgreSQL, and build dbt marts.",
    start_date=pendulum.datetime(2026, 1, 1, tz="Asia/Ho_Chi_Minh"),
    schedule="0 */3 * * *",
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    on_failure_callback=mark_run_failed,
    tags=["stormwatch", "weather", "vietnam"],
) as weather_pipeline:
    start_run = BashOperator(
        task_id="start_run",
        bash_command=(
            f"{PYTHON} src/warehouse/load_postgres.py start "
            "--run-id '{{ run_id }}'"
        ),
        cwd=PROJECT_DIR,
    )

    fetch_weather = BashOperator(
        task_id="fetch_weather",
        bash_command=f"{PYTHON} src/ingestion/fetch_weather.py",
        cwd=PROJECT_DIR,
        execution_timeout=timedelta(minutes=20),
    )

    load_postgres = BashOperator(
        task_id="load_postgres",
        bash_command=(
            f"{PYTHON} src/warehouse/load_postgres.py load "
            "--run-id '{{ run_id }}'"
        ),
        cwd=PROJECT_DIR,
        execution_timeout=timedelta(minutes=10),
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="dbt build --project-dir dbt --profiles-dir dbt",
        cwd=PROJECT_DIR,
        execution_timeout=timedelta(minutes=20),
    )

    finish_run = BashOperator(
        task_id="finish_run",
        bash_command=(
            f"{PYTHON} src/warehouse/load_postgres.py finish "
            "--run-id '{{ run_id }}' --status success"
        ),
        cwd=PROJECT_DIR,
    )

    start_run >> fetch_weather >> load_postgres >> dbt_build >> finish_run


with DAG(
    dag_id="stormwatch_refresh_locations",
    description="Manually refresh and geocode Vietnam province reference data.",
    start_date=pendulum.datetime(2026, 1, 1, tz="Asia/Ho_Chi_Minh"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["stormwatch", "reference-data", "vietnam"],
) as refresh_locations:
    fetch_provinces = BashOperator(
        task_id="fetch_provinces",
        bash_command=f"{PYTHON} src/ingestion/fetch_vietnam_provinces.py",
        cwd=PROJECT_DIR,
        execution_timeout=timedelta(minutes=5),
    )

    enrich_coordinates = BashOperator(
        task_id="enrich_coordinates",
        bash_command=f"{PYTHON} src/ingestion/coordinates_enrich.py",
        cwd=PROJECT_DIR,
        execution_timeout=timedelta(minutes=15),
    )

    load_locations = BashOperator(
        task_id="load_locations",
        bash_command=f"{PYTHON} src/warehouse/load_postgres.py locations --run-id '{{{{ run_id }}}}'",
        cwd=PROJECT_DIR,
        execution_timeout=timedelta(minutes=5),
    )

    fetch_provinces >> enrich_coordinates >> load_locations
