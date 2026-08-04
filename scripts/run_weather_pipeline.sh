#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="/home/ubuntu/StormWatch-Vietnam"
LOCK_FILE="/tmp/stormwatch-weather-pipeline.lock"

cd "$PROJECT_DIR"

exec 9>"$LOCK_FILE"

if ! flock -n 9; then
    echo "$(date -Is) Pipeline skipped: another run is active."
    exit 0
fi

RUN_ID="cron__$(date -u +%Y-%m-%dT%H:%M:%SZ)"

run_in_container() {
    docker compose --profile pipeline run --rm pipeline "$@"
}

mark_failed() {
    local exit_code=$?
    local error="Pipeline failed during scheduled execution"

    echo "$(date -Is) Pipeline failed: $RUN_ID"

    run_in_container \
        python src/warehouse/load_postgres.py finish \
        --run-id "$RUN_ID" \
        --status failed \
        --error "$error" || true

    exit "$exit_code"
}

trap mark_failed ERR

echo "=================================================="
echo "$(date -Is) Starting StormWatch weather pipeline"
echo "$(date -Is) Run ID: $RUN_ID"
echo "=================================================="

run_in_container \
    python src/warehouse/load_postgres.py start \
    --run-id "$RUN_ID"

run_in_container \
    python src/ingestion/fetch_weather.py

run_in_container \
    python src/warehouse/load_postgres.py load \
    --run-id "$RUN_ID"

run_in_container \
    dbt build \
    --project-dir dbt \
    --profiles-dir dbt

run_in_container \
    python src/warehouse/load_postgres.py finish \
    --run-id "$RUN_ID" \
    --status success

trap - ERR

echo "$(date -Is) Pipeline completed successfully: $RUN_ID"
