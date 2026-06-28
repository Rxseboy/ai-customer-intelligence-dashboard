"""
src/back_end/ml/data_loader.py
================================
Singleton SQLAlchemy engine dengan connection pool management.

MASALAH SEBELUMNYA:
  - get_engine() membuat engine BARU setiap kali dipanggil
  - Setiap engine = pool baru = N koneksi baru ke Supabase
  - Supabase session mode limit: 15 koneksi total → EMAXCONNSESSION

SOLUSI:
  - Singleton engine (dibuat sekali, digunakan bersama semua request)
  - pool_size=3, max_overflow=2 → max 5 koneksi total
  - pool_recycle=300 → koneksi idle > 5 menit di-recycle
  - pool_timeout=10 → request menunggu maks 10 detik sebelum error
  - pool_pre_ping=True → deteksi koneksi mati sebelum digunakan

UPGRADE OPSIONAL (direkomendasikan Supabase):
  Ganti port 5432 (session mode) → 6543 (transaction mode) di .env
  Transaction mode tidak mengikat koneksi selama sesi, jauh lebih efisien.
"""

import os
import threading
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Singleton engine ─────────────────────────────────────────────────────────
_engine       = None
_engine_lock  = threading.Lock()


def get_engine():
    """
    Return a shared SQLAlchemy engine (created once, reused forever).
    Thread-safe via double-checked locking.
    """
    global _engine
    if _engine is not None:
        return _engine

    with _engine_lock:
        if _engine is not None:          # re-check after acquiring lock
            return _engine

        database_url = os.getenv("DATABASE_URL")
        if database_url:
            url = database_url
        else:
            u    = os.getenv("DB_USER",     "postgres")
            p    = os.getenv("DB_PASSWORD", "")
            h    = os.getenv("DB_HOST",     "localhost")
            port = os.getenv("DB_PORT",     "5432")
            db   = os.getenv("DB_NAME",     "postgres")
            url  = f"postgresql://{u}:{p}@{h}:{port}/{db}"

        _engine = create_engine(
            url,
            # ── Pool configuration ──────────────────────────────────────────
            # Stay well under Supabase session-mode limit (15 total)
            pool_size       = 3,      # persistent connections kept alive
            max_overflow    = 2,      # burst connections (returned immediately after use)
            # ── Stability ───────────────────────────────────────────────────
            pool_pre_ping   = True,   # test connection health before use
            pool_recycle    = 300,    # recycle connections idle > 5 minutes
            pool_timeout    = 10,     # wait max 10 s for a free connection
            # ── Supabase-specific ────────────────────────────────────────────
            # keepalives reduce "connection reset" errors on long idle periods
            connect_args    = {
                "options":            "-c statement_timeout=30000",  # 30 s query limit
                "keepalives":         1,
                "keepalives_idle":    30,
                "keepalives_interval": 5,
                "keepalives_count":   3,
            },
        )
        logger.info("[DB] ✅ Singleton engine created (pool_size=3, max_overflow=2)")
        return _engine


def dispose_engine():
    """Call this on application shutdown to release all connections."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
        logger.info("[DB] 🛑 Engine disposed — all connections released")


# ── Data loading helpers ─────────────────────────────────────────────────────

def load_orders(engine=None) -> pd.DataFrame:
    """Load fact_orders (valid status only)."""
    if engine is None:
        engine = get_engine()
    q = text("""
        SELECT order_id, customer_id, product_id, order_date,
               sale_price, status
        FROM fact_orders
        WHERE status NOT IN ('Cancelled', 'Returned')
    """)
    df = pd.read_sql(q, engine)
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def load_customers(engine=None) -> pd.DataFrame:
    """Load dim_customers."""
    if engine is None:
        engine = get_engine()
    return pd.read_sql("SELECT * FROM dim_customers", engine)


def load_products(engine=None) -> pd.DataFrame:
    """Load dim_products."""
    if engine is None:
        engine = get_engine()
    return pd.read_sql("SELECT * FROM dim_products", engine)


def load_full(engine=None) -> pd.DataFrame:
    """Load joined dataset (orders + customers + products)."""
    if engine is None:
        engine = get_engine()
    q = text("""
        SELECT
            fo.order_id, fo.order_item_id, fo.order_date,
            fo.sale_price, fo.status,
            dc.customer_id, dc.age, dc.gender, dc.country, dc.city,
            dp.product_id, dp.name AS product_name,
            dp.category, dp.brand, dp.retail_price, dp.cost
        FROM fact_orders fo
        LEFT JOIN dim_customers dc ON fo.customer_id = dc.customer_id
        LEFT JOIN dim_products  dp ON fo.product_id  = dp.product_id
        WHERE fo.status NOT IN ('Cancelled', 'Returned')
    """)
    df = pd.read_sql(q, engine)
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


if __name__ == "__main__":
    eng = get_engine()
    df  = load_orders(eng)
    print(f"Loaded {len(df):,} rows from fact_orders")
    print(df.head(3))
