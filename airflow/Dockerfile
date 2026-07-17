FROM apache/airflow:3.3.0-python3.12

COPY airflow/requirements.txt /tmp/stormwatch-requirements.txt
RUN pip install --no-cache-dir -r /tmp/stormwatch-requirements.txt
