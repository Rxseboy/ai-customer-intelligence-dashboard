"""
setup_db.py
===========
Script untuk membuat database dan schema PostgreSQL sebelum menjalankan pipeline.
Semua konfigurasi dibaca otomatis dari file .env

Cara menjalankan:
    python setup_db.py
"""

import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Load .env otomatis dari root folder (satu tingkat di atas folder scripts)
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ==============================================================================
# KONFIGURASI — dibaca dari .env
# ==============================================================================
PG_USER     = os.getenv("DB_USER",     "admin")
PG_PASSWORD = os.getenv("DB_PASSWORD", "admin")
PG_HOST     = os.getenv("DB_HOST",     "localhost")
PG_PORT     = os.getenv("DB_PORT",     "5432")
DB_NAME     = os.getenv("DB_NAME",     "thelook_ecommerce")

# ==============================================================================
# SQL DDL (CREATE TABLE)
# ==============================================================================
DDL_STATEMENTS = [
    # Hapus tabel jika sudah ada (aman untuk reset)
    "DROP TABLE IF EXISTS fact_orders CASCADE;",
    "DROP TABLE IF EXISTS dim_customers CASCADE;",
    "DROP TABLE IF EXISTS dim_products CASCADE;",
    "DROP TABLE IF EXISTS dim_date CASCADE;",

    # dim_customers
    """
    CREATE TABLE IF NOT EXISTS dim_customers (
        customer_id     BIGINT PRIMARY KEY,
        first_name      VARCHAR(100),
        last_name       VARCHAR(100),
        email           VARCHAR(200),
        gender          VARCHAR(20),
        age             INT,
        city            VARCHAR(100),
        state           VARCHAR(100),
        country         VARCHAR(10),
        created_at      TIMESTAMP
    );
    """,

    # dim_products
    """
    CREATE TABLE IF NOT EXISTS dim_products (
        product_id      BIGINT PRIMARY KEY,
        name            VARCHAR(500),
        category        VARCHAR(100),
        brand           VARCHAR(200),
        department      VARCHAR(100),
        retail_price    NUMERIC(10, 2),
        cost            NUMERIC(10, 2)
    );
    """,

    # dim_date
    """
    CREATE TABLE IF NOT EXISTS dim_date (
        date_id         INT PRIMARY KEY,
        full_date       DATE,
        year            INT,
        quarter         INT,
        month           INT,
        month_name      VARCHAR(20),
        week            INT,
        day_of_week     INT,
        day_name        VARCHAR(15),
        is_weekend      BOOLEAN
    );
    """,

    # fact_orders
    """
    CREATE TABLE IF NOT EXISTS fact_orders (
        fact_id         BIGSERIAL PRIMARY KEY,
        order_id        BIGINT,
        order_item_id   BIGINT,
        customer_id     BIGINT,
        product_id      BIGINT,
        date_id         INT,
        order_date      TIMESTAMP,
        sale_price      NUMERIC(10, 2),
        status          VARCHAR(50),
        margin          NUMERIC(10, 2)
    );
    """,

    # Index untuk performa query
    "CREATE INDEX IF NOT EXISTS idx_fact_customer ON fact_orders(customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_fact_product  ON fact_orders(product_id);",
    "CREATE INDEX IF NOT EXISTS idx_fact_date     ON fact_orders(date_id);",
    "CREATE INDEX IF NOT EXISTS idx_fact_order    ON fact_orders(order_id);",
]


def create_database() -> None:
    """Membuat database thelook_ecommerce jika belum ada."""
    # Connect ke database 'postgres' default dulu
    admin_url = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/postgres"
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    with engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        )
        exists = result.fetchone()
        if not exists:
            conn.execute(text(f"CREATE DATABASE {DB_NAME}"))
            logger.info(f"✅ Database '{DB_NAME}' berhasil dibuat.")
        else:
            logger.info(f"ℹ️  Database '{DB_NAME}' sudah ada, dilanjutkan.")
    engine.dispose()


def create_schema() -> None:
    """Membuat tabel-tabel star schema di database."""
    db_url = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{DB_NAME}"
    engine = create_engine(db_url)

    with engine.begin() as conn:
        for stmt in DDL_STATEMENTS:
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))

    logger.info("✅ Schema star schema berhasil dibuat di database.")
    engine.dispose()


def main():
    logger.info("=" * 50)
    logger.info("SETUP DATABASE PostgreSQL")
    logger.info(f"  Host     : {PG_HOST}:{PG_PORT}")
    logger.info(f"  Database : {DB_NAME}")
    logger.info(f"  User     : {PG_USER}")
    logger.info("=" * 50)

    if not PG_PASSWORD:
        logger.error("❌ DB_PASSWORD tidak ditemukan di file .env!")
        logger.error("Pastikan file .env sudah berisi: DB_PASSWORD=<password_kamu>")
        return

    try:
        logger.info(f"[1/2] Membuat database '{DB_NAME}'...")
        create_database()

        logger.info(f"[2/2] Membuat schema (tabel + index)...")
        create_schema()

        logger.info("\n✅ Setup selesai! Sekarang jalankan: python pipeline.py")

    except Exception as e:
        logger.error(f"❌ Setup gagal: {e}")
        logger.error("\nPastikan:")
        logger.error("  1. Kredensial Database Supabase / PostgreSQL valid dan koneksi online")
        logger.error("  2. DB_PASSWORD di file .env sudah benar")
        logger.error("  3. Library psycopg2-binary sudah terinstall")
        raise


if __name__ == "__main__":
    main()
