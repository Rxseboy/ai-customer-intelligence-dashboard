"""
dags/ecommerce_etl.py
=====================
Airflow DAG untuk ETL Pipeline thelook_ecommerce.

Alur:
  extract_data → transform_data → load_data

Inter-task storage: Parquet files di /opt/airflow/data/
  - /opt/airflow/data/raw/{table}.parquet     (output extract)
  - /opt/airflow/data/processed/{table}.parquet (output transform)

Schedule: @daily (jalan otomatis setiap hari)
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from airflow import DAG
from airflow.operators.python import PythonOperator

# Load .env
load_dotenv(dotenv_path="/opt/airflow/.env")

logger = logging.getLogger(__name__)

# ==============================================================================
# PATHS
# ==============================================================================
DATA_DIR        = Path("/opt/airflow/data")
RAW_DIR         = DATA_DIR / "raw"
PROCESSED_DIR   = DATA_DIR / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# TASK FUNCTIONS
# ==============================================================================

def task_extract(**context) -> None:
    """
    Task 1: Extract semua tabel dari BigQuery → validasi → simpan ke Parquet.
    Output: /opt/airflow/data/raw/{table}.parquet
    """
    import sys
    sys.path.insert(0, "/opt/airflow")

    from etl.extract  import extract_all_tables
    from etl.validate import validate_all_tables

    logger.info("=" * 55)
    logger.info("  TASK: EXTRACT")
    logger.info("=" * 55)

    raw_data = extract_all_tables()

    # ── Data Validation ──────────────────────────────────────────────────────
    logger.info("Menjalankan data validation...")
    validate_all_tables(raw_data)

    for table_name, df in raw_data.items():
        path = RAW_DIR / f"{table_name}.parquet"
        df.to_parquet(path, index=False, engine="pyarrow")
        logger.info(f"  💾 Saved: {path} ({len(df):,} baris)")

    logger.info(f"Extract + Validation selesai → {len(raw_data)} file Parquet di {RAW_DIR}")


def task_transform(**context) -> None:
    """
    Task 2: Baca Parquet raw → clean + bangun Star Schema → simpan Parquet.
    Input : /opt/airflow/data/raw/{table}.parquet
    Output: /opt/airflow/data/processed/{table}.parquet
    """
    import sys
    sys.path.insert(0, "/opt/airflow")

    from etl.transform import (
        clean_orders, clean_order_items, clean_users, clean_products,
        build_dim_customers, build_dim_products, build_dim_date,
        build_fact_orders
    )

    logger.info("=" * 55)
    logger.info("  TASK: TRANSFORM")
    logger.info("=" * 55)

    # Baca raw Parquet
    logger.info("Membaca raw Parquet files...")
    orders          = pd.read_parquet(RAW_DIR / "orders.parquet")
    order_items     = pd.read_parquet(RAW_DIR / "order_items.parquet")
    users           = pd.read_parquet(RAW_DIR / "users.parquet")
    products        = pd.read_parquet(RAW_DIR / "products.parquet")

    # Clean
    logger.info("[1/2] Cleaning data...")
    orders          = clean_orders(orders)
    order_items     = clean_order_items(order_items)
    users           = clean_users(users)
    products        = clean_products(products)

    # Build Star Schema
    logger.info("[2/2] Membangun Star Schema...")
    dim_customers   = build_dim_customers(users)
    dim_products    = build_dim_products(products)
    dim_date        = build_dim_date(orders["created_at"].min(), orders["created_at"].max())
    fact_orders     = build_fact_orders(order_items, orders)

    star_schema = {
        "dim_customers": dim_customers,
        "dim_products":  dim_products,
        "dim_date":      dim_date,
        "fact_orders":   fact_orders,
    }

    # Simpan ke Parquet
    for table_name, df in star_schema.items():
        path = PROCESSED_DIR / f"{table_name}.parquet"
        df.to_parquet(path, index=False, engine="pyarrow")
        logger.info(f"  💾 Saved: {path} ({len(df):,} baris)")

    logger.info("Transform selesai!")


def task_load(**context) -> None:
    """
    Task 3: Baca Parquet processed → load ke PostgreSQL.
    Input: /opt/airflow/data/processed/{table}.parquet
    """
    import sys
    sys.path.insert(0, "/opt/airflow")

    from etl.load import connect_db, load_all, verify_load

    logger.info("=" * 55)
    logger.info("  TASK: LOAD")
    logger.info("=" * 55)

    # Baca semua processed Parquet
    load_order = ["dim_customers", "dim_products", "dim_date", "fact_orders"]
    star_schema = {}

    for table_name in load_order:
        path = PROCESSED_DIR / f"{table_name}.parquet"
        if path.exists():
            df = pd.read_parquet(path)
            star_schema[table_name] = df
            logger.info(f"  📂 Loaded: {path} ({len(df):,} baris)")
        else:
            logger.warning(f"  ⚠️  File tidak ditemukan: {path}")

    # Load ke PostgreSQL
    engine = connect_db()
    load_all(star_schema, engine)
    verify_load(engine)

    logger.info("Load selesai!")


# ==============================================================================
# DAG DEFINITION
# ==============================================================================
default_args = {
    "owner":            "rizqi",
    "depends_on_past":  False,
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
}

with DAG(
    dag_id="ecommerce_etl_pipeline",
    description="ETL pipeline: BigQuery thelook_ecommerce → PostgreSQL Star Schema",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="@daily",       # Airflow 3.x: gunakan 'schedule' bukan 'schedule_interval'
    catchup=False,
    tags=["etl", "ecommerce", "bigquery", "postgresql"],
) as dag:

    extract = PythonOperator(
        task_id="extract_data",
        python_callable=task_extract,
    )

    transform = PythonOperator(
        task_id="transform_data",
        python_callable=task_transform,
    )

    load = PythonOperator(
        task_id="load_data",
        python_callable=task_load,
    )

    # Dependency chain
    extract >> transform >> load
