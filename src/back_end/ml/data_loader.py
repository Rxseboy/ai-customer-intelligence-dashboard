"""
models/data_loader.py
Load data dari PostgreSQL ke pandas DataFrame.
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


def get_engine():
    """
    Buat SQLAlchemy engine dari .env.
    Prioritas: DATABASE_URL > DB_USER/DB_PASSWORD/DB_HOST/...
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(database_url, pool_pre_ping=True)

    u    = os.getenv("DB_USER",     "postgres")
    p    = os.getenv("DB_PASSWORD", "")
    h    = os.getenv("DB_HOST",     "localhost")
    port = os.getenv("DB_PORT",     "5432")
    db   = os.getenv("DB_NAME",     "postgres")
    return create_engine(f"postgresql://{u}:{p}@{h}:{port}/{db}", pool_pre_ping=True)


def load_orders(engine=None) -> pd.DataFrame:
    """Load fact_orders (hanya status valid)."""
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
