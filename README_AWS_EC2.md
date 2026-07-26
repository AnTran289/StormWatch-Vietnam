# StormWatch Vietnam — AWS EC2 Deployment

StormWatch Vietnam is a data-engineering portfolio project that transforms hourly weather forecasts into prototype rainfall, storm, and flood-risk indicators for Vietnam's 34 provincial-level administrative units.

This version deploys the PostgreSQL warehouse, dbt transformations, data-loading pipeline, and Streamlit dashboard to an Ubuntu virtual machine hosted on Amazon EC2.

> **Disclaimer:** This project is for educational and portfolio purposes. Its risk indicators are experimental and must not be used as official weather forecasts or disaster warnings.

---

## Cloud Deployment Overview

The local version runs the database and application from a developer machine.

The AWS version runs the project continuously on an EC2 Ubuntu instance.

| Area | Local Version | AWS Version |
|---|---|---|
| Host environment | Windows development machine | Ubuntu EC2 virtual machine |
| Application access | `http://localhost:8501` | `http://<EC2_PUBLIC_IP>:8501` |
| Database | PostgreSQL in Docker locally | PostgreSQL container on EC2 |
| Dashboard | Started from local terminal | Docker container on EC2 |
| dbt execution | Local Python environment | Executed inside the dashboard container |
| Pipeline trigger | Manual local commands | Manual commands over SSH |
| Availability | Only while the local machine is running | Available while the EC2 instance is running |
| Authentication | Local machine access | EC2 SSH key pair |
| Networking | Localhost | AWS security groups and public IPv4 |
| Orchestration | Local/manual | Manual; Airflow disabled on current EC2 size |

---

## Architecture

```text
Public APIs
|-- Open-Meteo
|-- OpenStreetMap
`-- Vietnam Provinces API
        |
        v
Python ingestion scripts
        |
        v
Processed CSV files
        |
        v
PostgreSQL on Amazon EC2
|-- raw.weather_hourly
|-- analytics.dim_locations
`-- metadata.pipeline_runs
        |
        v
dbt Core
|-- analytics_staging
|-- analytics_intermediate
`-- analytics_marts
        |
        v
Streamlit dashboard
        |
        v
EC2 public IPv4 address
```

The project currently processes:

- 34 Vietnamese provincial-level administrative units
- 5,712 hourly weather forecast records
- 34 rows in the latest province risk snapshot

---

## AWS Services Used

| AWS Service | Purpose |
|---|---|
| Amazon EC2 | Hosts the Ubuntu virtual machine |
| EC2 Security Groups | Controls SSH and dashboard network access |
| Amazon EBS | Stores the VM filesystem and Docker data |
| AWS IAM | Controls access to the AWS account |
| Amazon CloudWatch | Can be used for instance and billing monitoring |

---

## Technology Stack

- Python
- PostgreSQL
- dbt Core
- Streamlit
- Docker
- Docker Compose
- SQLAlchemy
- Amazon EC2
- Ubuntu
- Git and GitHub

---

## Project Structure

```text
StormWatch-Vietnam/
|-- dashboard/
|   `-- app.py
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
|       `-- init.sql
|-- src/
|   |-- ingestion/
|   |   |-- fetch_vietnam_provinces.py
|   |   |-- coordinates_enrich.py
|   |   `-- fetch_weather.py
|   `-- warehouse/
|       `-- load_postgres.py
|-- data/
|   |-- processed/
|   |-- raw/
|   `-- reference/
|-- .env.example
|-- compose.yaml
|-- requirements.txt
`-- README.md
```

---

## Prerequisites

### AWS

- An AWS account
- An EC2 instance running Ubuntu
- An EC2 key pair in `.pem` format
- A security group allowing:
  - TCP port `22` for SSH
  - TCP port `8501` for Streamlit

For better security, restrict port `22` to your own public IP instead of allowing access from everywhere.

### EC2 Instance

The Ubuntu VM requires:

- Git
- Docker Engine
- Docker Compose
- Enough memory to run PostgreSQL and Streamlit

The current deployment does not run Airflow because the selected EC2 instance experienced memory exhaustion when Airflow was enabled.

---

## Connect to the EC2 Instance

From Windows PowerShell:

```powershell
ssh -i "C:\path\to\your-key.pem" ubuntu@<EC2_PUBLIC_IP>
```

Example:

```powershell
ssh -i "C:\Users\YourName\stormwatch-key.pem" ubuntu@12.34.56.78
```

After connecting:

```bash
cd ~/StormWatch-Vietnam
```

---

## Clone the AWS Deployment Branch

Using SSH:

```bash
git clone -b aws-deployment git@github.com:AnTran289/StormWatch-Vietnam.git
cd StormWatch-Vietnam
```

Using HTTPS:

```bash
git clone -b aws-deployment https://github.com/AnTran289/StormWatch-Vietnam.git
cd StormWatch-Vietnam
```

---

## Configure Environment Variables

Create the environment file:

```bash
cp .env.example .env
```

Edit it:

```bash
nano .env
```

Example configuration:

```env
DB_HOST=postgres
DB_PORT=5432
DB_NAME=stormwatch
DB_USER=stormwatch_user
DB_PASSWORD=replace_with_a_secure_password
```

Inside Docker Compose, `DB_HOST` should normally use the PostgreSQL service name:

```env
DB_HOST=postgres
```

Do not commit `.env`, AWS keys, SSH private keys, or database passwords.

---

## Start the Deployment

Build and start the containers:

```bash
docker compose up --build -d
```

Check container status:

```bash
docker compose ps
```

View dashboard logs:

```bash
docker compose logs --tail=100 dashboard
```

View PostgreSQL logs:

```bash
docker compose logs --tail=100 postgres
```

---

## Run the Pipeline Manually

Create a unique pipeline run ID:

```bash
RUN_ID="manual-$(date +%Y%m%d-%H%M%S)"
echo "$RUN_ID"
```

Example:

```text
manual-20260725-183500
```

Use the same run ID throughout the pipeline.

### 1. Start the pipeline run

```bash
docker compose exec dashboard \
  python -m src.warehouse.load_postgres start \
  --run-id "$RUN_ID"
```

### 2. Refresh province reference data

These steps do not necessarily need to run during every weather refresh.

```bash
docker compose exec dashboard \
  python -m src.ingestion.fetch_vietnam_provinces

docker compose exec dashboard \
  python -m src.ingestion.coordinates_enrich
```

### 3. Fetch weather data

```bash
docker compose exec dashboard \
  python -m src.ingestion.fetch_weather
```

### 4. Load locations

```bash
docker compose exec dashboard \
  python -m src.warehouse.load_postgres locations \
  --run-id "$RUN_ID"
```

### 5. Load weather records

```bash
docker compose exec dashboard \
  python -m src.warehouse.load_postgres load \
  --run-id "$RUN_ID"
```

### 6. Run dbt transformations and tests

```bash
docker compose exec dashboard bash -c \
  "cd /app/dbt && dbt build"
```

### 7. Mark the pipeline run as successful

```bash
docker compose exec dashboard \
  python -m src.warehouse.load_postgres finish \
  --run-id "$RUN_ID" \
  --status success
```

If the pipeline fails, record the run as failed:

```bash
docker compose exec dashboard \
  python -m src.warehouse.load_postgres finish \
  --run-id "$RUN_ID" \
  --status failed
```

---

## Verify the Data Warehouse

Check weather records:

```bash
docker compose exec postgres psql \
  -U stormwatch_user \
  -d stormwatch \
  -c "SELECT COUNT(*) FROM raw.weather_hourly;"
```

Expected result for the current dataset:

```text
5712
```

Check province locations:

```bash
docker compose exec postgres psql \
  -U stormwatch_user \
  -d stormwatch \
  -c "SELECT COUNT(*) FROM analytics.dim_locations;"
```

Expected result:

```text
34
```

Check the province risk snapshot:

```bash
docker compose exec postgres psql \
  -U stormwatch_user \
  -d stormwatch \
  -c "SELECT COUNT(*) FROM analytics_marts.province_risk_snapshot;"
```

Expected result:

```text
34
```

Check recent pipeline runs:

```bash
docker compose exec postgres psql \
  -P pager=off \
  -U stormwatch_user \
  -d stormwatch \
  -c "
SELECT
    pipeline_name,
    status,
    airflow_run_id,
    started_at,
    completed_at
FROM metadata.pipeline_runs
ORDER BY started_at DESC
LIMIT 10;
"
```

---

## Access the Dashboard

Open:

```text
http://<EC2_PUBLIC_IP>:8501
```

Example:

```text
http://12.34.56.78:8501
```

The dashboard provides:

- National risk metrics
- Province monitoring map
- Risk-level distribution
- Priority-province table
- Province search
- Rainfall and wind charts
- Detailed province snapshots
- Recent pipeline-run status

The EC2 security group must allow inbound traffic on port `8501`.

---

## Stop and Restart the Deployment

Stop containers without deleting the PostgreSQL volume:

```bash
docker compose down
```

Start them again:

```bash
docker compose up -d
```

Restart only the dashboard:

```bash
docker compose restart dashboard
```

Restart PostgreSQL:

```bash
docker compose restart postgres
```

---

## EC2 Lifecycle

Closing the SSH terminal does not stop the EC2 instance.

The dashboard remains available while:

- The EC2 instance is running
- The Docker containers are running
- The security group allows port `8501`

To avoid unnecessary AWS charges, stop the EC2 instance when the deployment is not needed.

Stopping the instance preserves the EBS volume. Terminating the instance may permanently delete its storage, depending on the configured volume settings.

The public IPv4 address may change after stopping and starting the instance unless an Elastic IP is attached.

---

## Airflow Status

Airflow is included in the broader StormWatch architecture but is currently disabled in this EC2 deployment.

The selected EC2 instance ran out of memory when PostgreSQL, Streamlit, and Airflow were running together.

Airflow can be enabled later by:

- Upgrading to an EC2 instance with more memory
- Running Airflow on a separate instance
- Using Amazon Managed Workflows for Apache Airflow
- Replacing Airflow temporarily with cron or GitHub Actions

For the current deployment:

```bash
docker compose stop airflow
docker compose rm -f airflow
```

---

## Security Notes

Never commit:

```text
.env
*.pem
.streamlit/secrets.toml
AWS access keys
database passwords
private SSH keys
```

Recommended practices:

- Restrict SSH access to your current public IP
- Use a strong PostgreSQL password
- Use SSH authentication for GitHub
- Enable MFA on the AWS account
- Configure AWS billing alerts
- Avoid exposing PostgreSQL port `5432` publicly
- Use HTTPS and a reverse proxy before treating the dashboard as a public production service

---

## Limitations

- Risk thresholds are experimental
- The model does not include river levels, drainage capacity, terrain, soil moisture, or official warning feeds
- The dashboard currently uses HTTP rather than HTTPS
- The EC2 public IP may change after the instance is restarted
- The current pipeline requires manual execution
- Airflow is disabled due to the memory limits of the current EC2 instance
- The deployment is a portfolio environment, not a production disaster-warning platform

---

## Future Improvements

- Automate refreshes with cron, GitHub Actions, or Airflow
- Attach an Elastic IP
- Configure a domain name
- Add HTTPS through Nginx and Let's Encrypt
- Store secrets in AWS Systems Manager Parameter Store
- Publish Docker images to Amazon ECR
- Add CloudWatch monitoring and alarms
- Provision infrastructure with Terraform
- Migrate PostgreSQL to Amazon RDS
- Deploy the dashboard behind an Application Load Balancer

---

## Author

**An Tran**

Data Engineering Portfolio Project

[GitHub](https://github.com/AnTran289)
