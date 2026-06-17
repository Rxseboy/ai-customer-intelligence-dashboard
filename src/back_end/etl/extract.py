"""
etl/extract.py
==============
Module ETL untuk mengambil data dari Google BigQuery.
Digunakan oleh Airflow DAG dan pipeline.py langsung.
"""

import os
import logging
from dotenv import load_dotenv
from google.cloud import bigquery
import pandas as pd

# Load .env — coba dari beberapa lokasi (root project atau AIRFLOW_HOME)
for env_path in [
    os.path.join(os.path.dirname(__file__), "..", ".env"),
    os.path.join("/opt/airflow", ".env"),
    ".env",
]:
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
        break

logger = logging.getLogger(__name__)


def get_bigquery_client() -> bigquery.Client:
    """Membuat BigQuery client dari GOOGLE_APPLICATION_CREDENTIALS di .env."""
    key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "key.json")
    if not os.path.exists(key_path):
        raise FileNotFoundError(
            f"File kredensial tidak ditemukan: '{key_path}'\n"
            "Pastikan GOOGLE_APPLICATION_CREDENTIALS sudah diisi di .env"
        )
    logger.info(f"BigQuery client menggunakan kredensial: {key_path}")
    return bigquery.Client()


def get_data(table_name: str) -> pd.DataFrame:
    """Mengambil SELURUH data dari satu tabel BigQuery thelook_ecommerce."""
    client = get_bigquery_client()
    query = f"""
        SELECT *
        FROM `bigquery-public-data.thelook_ecommerce.{table_name}`
    """
    logger.info(f"Mengambil SEMUA data dari tabel: {table_name}...")
    df = client.query(query).to_dataframe()
    logger.info(f"  ✅ {table_name}: {len(df):,} baris, {len(df.columns)} kolom")
    return df


def extract_all_tables() -> dict:
    """
    Mengambil semua tabel thelook_ecommerce dari BigQuery.

    Returns:
        dict {nama_tabel: DataFrame}
    """
    tables = ["orders", "order_items", "users", "products", "inventory_items"]
    raw_data = {}

    logger.info("=" * 50)
    logger.info("EXTRACT: Mengambil SEMUA data dari BigQuery")
    logger.info("=" * 50)

    for table in tables:
        try:
            raw_data[table] = get_data(table)
        except Exception as e:
            logger.error(f"  ❌ Gagal mengambil '{table}': {e}")
            raise

    logger.info(f"Extract selesai: {len(raw_data)}/{len(tables)} tabel.")
    return raw_data
