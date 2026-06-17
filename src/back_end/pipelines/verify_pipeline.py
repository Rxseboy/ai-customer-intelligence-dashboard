"""
verify_pipeline.py
==================
Script untuk memverifikasi hasil pipeline tanpa perlu masuk ke psql.
Menampilkan jumlah baris, sample data, dan validasi star schema.

Cara menjalankan:
    python verify_pipeline.py
"""

import logging
import pandas as pd
from sqlalchemy import text
from src.back_end.etl.load import connect_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TABLES = ["dim_customers", "dim_products", "dim_date", "fact_orders"]


def run_verification():
    print("\n" + "=" * 60)
    print("  ✅ VERIFIKASI HASIL ETL PIPELINE")
    print("=" * 60)

    engine = connect_db()

    # ------------------------------------------------------------------
    # 1. Cek jumlah baris
    # ------------------------------------------------------------------
    print("\n📊 Jumlah Baris per Tabel:")
    print(f"  {'Tabel':<25} {'Jumlah Baris':>15}")
    print("  " + "-" * 42)
    with engine.connect() as conn:
        for table in TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table:<25} {count:>15,}")

    # ------------------------------------------------------------------
    # 2. Sample fact_orders
    # ------------------------------------------------------------------
    print("\n📋 Sample fact_orders (5 baris):")
    df = pd.read_sql("SELECT * FROM fact_orders LIMIT 5", engine)
    print(df.to_string(index=False))

    # ------------------------------------------------------------------
    # 3. Revenue per bulan
    # ------------------------------------------------------------------
    print("\n📈 Revenue per Bulan (Top 5):")
    query = """
        SELECT
            d.year,
            d.month_name,
            COUNT(f.fact_id)       AS total_transaksi,
            ROUND(SUM(f.sale_price)::numeric, 2) AS total_revenue
        FROM fact_orders f
        JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY d.year, d.month, d.month_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    df_rev = pd.read_sql(query, engine)
    print(df_rev.to_string(index=False))

    # ------------------------------------------------------------------
    # 4. Top 5 produk terlaris
    # ------------------------------------------------------------------
    print("\n🏆 Top 5 Produk Terlaris:")
    query2 = """
        SELECT
            p.name                  AS produk,
            p.category,
            COUNT(f.fact_id)        AS jumlah_terjual,
            ROUND(SUM(f.sale_price)::numeric, 2) AS total_revenue
        FROM fact_orders f
        JOIN dim_products p ON f.product_id = p.product_id
        GROUP BY p.name, p.category
        ORDER BY jumlah_terjual DESC
        LIMIT 5
    """
    df_prod = pd.read_sql(query2, engine)
    print(df_prod.to_string(index=False))

    print("\n✅ Verifikasi selesai. Database siap digunakan!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_verification()
