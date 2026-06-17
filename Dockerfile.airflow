# ==============================================================================
# UNIFIED DOCKERFILE
# Mencakup: Apache Airflow (ETL) + FastAPI (API) + React (Served separately or statically)
# Python: 3.11 | Airflow: 2.9.1
# ==============================================================================
FROM apache/airflow:2.9.1-python3.11

USER root

# Install system dependencies (psycopg2, xgboost, gcc)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq-dev \
       gcc \
       build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Salin requirements
COPY requirements-airflow.txt /requirements-airflow.txt
COPY requirements.txt /requirements.txt

# Install semua dependensi
# airflow-requirements dulu (BigQuery, SQLAlchemy, Pandas)
# kemudian requirements.txt (ML stack, API, Dashboard)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /requirements-airflow.txt \
    && pip install --no-cache-dir -r /requirements.txt

# Salin seluruh kode proyek ke direktori default Airflow (/opt/airflow)
COPY --chown=airflow:0 . /opt/airflow

# Working Directory
WORKDIR /opt/airflow

# PYTHONPATH — agar 'from src.back_end...' bisa diimport dari mana saja
ENV PYTHONPATH="/opt/airflow"
