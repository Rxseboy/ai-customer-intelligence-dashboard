"""
etl/load.py
===========
Module ETL untuk menyimpan data ke PostgreSQL.
Digunakan oleh Airflow DAG dan pipeline.py langsung.

Mode Load:
  full        : Replace semua data (cocok untuk initial load)
  incremental : Hanya append baris baru berdasarkan max(order_date)

DOCKER NOTE:
  Saat jalan di Docker, DB_HOST otomatis diset ke host.docker.internal
  via environment variable di docker-compose.yml.
"""

import os
import logging
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Load .env dari beberapa lokasi
for env_path in [
    os.path.join(os.path.dirname(__file__), "..", ".env"),
    os.path.join("/opt/airflow", ".env"),
    ".env",
]:
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
        break

logger = logging.getLogger(__name__)


def connect_db(
    user: str = None,
    password: str = None,
    host: str = None,
    port: str = None,
    dbname: str = None
) -> Engine:
    """
    Membuat koneksi ke PostgreSQL.
    Nilai dibaca dari environment variables (.env atau docker-compose override).

    Docker override di docker-compose.yml:
        DB_HOST=host.docker.internal  (untuk reach host PostgreSQL dari container)
    """
    user     = user     or os.getenv("DB_USER",     "postgres")
    password = password or os.getenv("DB_PASSWORD", "")
    host     = host     or os.getenv("DB_HOST",     "localhost")
    port     = port     or os.getenv("DB_PORT",     "5432")
    dbname   = dbname   or os.getenv("DB_NAME",     "postgres")

    # Jika DATABASE_URL sudah ada, gunakan langsung
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        url = database_url
    else:
        if not password:
            raise ValueError("DB_PASSWORD tidak ditemukan di environment variables!")
        url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

    engine = create_engine(url, pool_pre_ping=True)

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info(f"✅ Terhubung ke PostgreSQL: {host}:{port}/{dbname}")
    return engine


def load_data(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    if_exists: str = "replace",
    chunksize: int = 10_000
) -> None:
    """Menyimpan DataFrame ke tabel PostgreSQL (batch insert)."""
    logger.info(f"  Loading '{table_name}' ({len(df):,} baris)...")
    # Gunakan koneksi eksplisit + BEGIN/COMMIT agar SQLAlchemy 2.x
    # bisa rollback() ketika ada error di tengah batch insert.
    with engine.begin() as conn:
        try:
            df.to_sql(
                table_name,
                conn,
                if_exists=if_exists,
                index=False,
                chunksize=chunksize,
                method="multi"
            )
        except Exception:
            # engine.begin() otomatis rollback ketika exception muncul
            raise
    logger.info(f"    ✅ '{table_name}' berhasil disimpan")



def get_max_date(table: str, date_col: str, engine: Engine):
    """
    Ambil max value dari kolom tanggal di tabel PostgreSQL.
    Return None jika tabel belum ada.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(f"SELECT MAX({date_col}) FROM {table}")
            ).scalar()
        logger.info(f"  [{table}] max({date_col}) = {result}")
        return result
    except Exception:
        logger.info(f"  [{table}] Tabel belum ada → full load")
        return None


def load_incremental(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    date_col: str = "order_date",
    chunksize: int = 10_000,
) -> int:
    """
    Incremental load — hanya append baris yang lebih baru dari max(date_col) di PostgreSQL.

    Returns:
        Jumlah baris yang di-insert
    """
    max_existing = get_max_date(table_name, date_col, engine)

    if max_existing is None:
        # Tabel belum ada → full load
        logger.info(f"  [{table_name}] Full load: {len(df):,} baris")
        with engine.begin() as conn:
            df.to_sql(table_name, conn, if_exists="replace",
                      index=False, chunksize=chunksize, method="multi")
        return len(df)

    # Filter hanya baris baru
    df[date_col] = pd.to_datetime(df[date_col])
    new_rows = df[df[date_col] > pd.Timestamp(max_existing)]

    if new_rows.empty:
        logger.info(f"  [{table_name}] Tidak ada data baru (max={max_existing})")
        return 0

    with engine.begin() as conn:
        new_rows.to_sql(table_name, conn, if_exists="append",
                        index=False, chunksize=chunksize, method="multi")
    logger.info(f"  [{table_name}] Incremental: +{len(new_rows):,} baris (max={max_existing})")
    return len(new_rows)



def load_all(
    tables: dict,
    engine: Engine,
    mode: str = "full",
) -> None:
    """
    Simpan semua tabel star schema ke PostgreSQL.

    Args:
        tables : dict {nama_tabel: DataFrame}
        engine : SQLAlchemy engine
        mode   : 'full' (replace) atau 'incremental' (append only new rows)
    """
    logger.info("=" * 50)
    logger.info(f"LOAD: Menyimpan data ke PostgreSQL [mode={mode}]")
    logger.info("=" * 50)

    load_order = ["dim_customers", "dim_products", "dim_date", "fact_orders"]
    total_rows = 0

    for table_name in load_order:
        if table_name not in tables:
            logger.warning(f"  ⚠️  Tabel '{table_name}' tidak ditemukan, dilewati.")
            continue

        df = tables[table_name]

        if mode == "incremental" and table_name == "fact_orders":
            # Hanya fact_orders yang incremental — dimensi selalu di-refresh
            n = load_incremental(df, table_name, engine, date_col="order_date")
        else:
            load_data(df, table_name, engine, if_exists="replace")
            n = len(df)

        total_rows += n

    logger.info(f"Load selesai. Total {total_rows:,} baris → {len(load_order)} tabel.")


def verify_load(engine: Engine) -> None:
    """Verifikasi jumlah baris tiap tabel di PostgreSQL."""
    logger.info("📊 Verifikasi data di PostgreSQL:")
    tables = ["dim_customers", "dim_products", "dim_date", "fact_orders"]
    with engine.connect() as conn:
        for table in tables:
            try:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                logger.info(f"  {table:<20} → {count:>10,} baris")
            except Exception as e:
                logger.warning(f"  {table:<20} → ❌ Error: {e}")
