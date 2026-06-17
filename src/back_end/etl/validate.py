"""
etl/validate.py
===============
Data validation utilities untuk ETL pipeline.
Pastikan data berkualitas sebelum transform & load ke PostgreSQL.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised ketika data tidak memenuhi minimum quality requirements."""
    pass


def validate_dataframe(
    df: pd.DataFrame,
    name: str,
    min_rows: int = 1,
    max_null_pct: float = 0.30,
    required_cols: list = None,
) -> None:
    """
    Validasi DataFrame setelah extract dari BigQuery.

    Args:
        df           : DataFrame yang akan divalidasi
        name         : Nama tabel (untuk logging)
        min_rows     : Minimum jumlah baris yang diharapkan
        max_null_pct : Maksimum persentase null yang ditoleransi (default 30%)
        required_cols: List kolom yang WAJIB ada

    Raises:
        ValidationError jika gagal
    """
    errors = []

    # 1. Cek jumlah baris
    if len(df) < min_rows:
        errors.append(f"Terlalu sedikit baris: {len(df)} (minimum: {min_rows})")

    # 2. Cek kolom wajib
    if required_cols:
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            errors.append(f"Kolom wajib tidak ada: {missing}")

    # 3. Cek null percentage total
    if len(df) > 0:
        null_pct = df.isnull().sum().sum() / (df.shape[0] * df.shape[1])
        if null_pct > max_null_pct:
            errors.append(f"Terlalu banyak null: {null_pct:.1%} (max: {max_null_pct:.0%})")

    if errors:
        msg = f"[VALIDATION FAILED] {name}:\n  " + "\n  ".join(errors)
        logger.error(msg)
        raise ValidationError(msg)

    logger.info(
        f"[VALIDATION OK] {name}: {len(df):,} rows | "
        f"{df.isnull().sum().sum() / (df.shape[0]*df.shape[1]):.1%} null"
    )


def validate_all_tables(raw: dict) -> None:
    """
    Validasi semua tabel hasil extract dari BigQuery.

    Args:
        raw: dict berisi {nama_tabel: DataFrame}
    """
    rules = {
        "orders": {
            "min_rows": 1000,
            "required_cols": ["order_id", "user_id", "status", "created_at"],
        },
        "order_items": {
            "min_rows": 1000,
            "required_cols": ["id", "order_id", "user_id", "product_id", "sale_price"],
        },
        "users": {
            "min_rows": 100,
            "required_cols": ["id", "first_name", "last_name", "email"],
        },
        "products": {
            "min_rows": 100,
            "required_cols": ["id", "name", "category", "retail_price"],
        },
    }

    logger.info("=" * 50)
    logger.info("DATA VALIDATION: Memeriksa kualitas data BigQuery")
    logger.info("=" * 50)

    failed = []
    for table, df in raw.items():
        rule = rules.get(table, {})
        try:
            validate_dataframe(
                df, table,
                min_rows=rule.get("min_rows", 1),
                required_cols=rule.get("required_cols"),
            )
        except ValidationError as e:
            logger.error(str(e))
            failed.append(table)

    if failed:
        raise ValidationError(f"Validasi gagal untuk tabel: {failed}. Pipeline dihentikan.")

    logger.info("[VALIDATION] Semua tabel LULUS validasi ✅")


def validate_star_schema(transformed: dict) -> None:
    """
    Validasi hasil transform (star schema) sebelum di-load ke PostgreSQL.
    """
    rules = {
        "fact_orders": {
            "min_rows": 1000,
            "required_cols": ["order_id", "customer_id", "product_id", "sale_price", "order_date"],
        },
        "dim_customers": {
            "min_rows": 100,
            "required_cols": ["customer_id", "email"],
        },
        "dim_products": {
            "min_rows": 100,
            "required_cols": ["product_id", "name", "category"],
        },
        "dim_date": {
            "min_rows": 365,
            "required_cols": ["date_id", "full_date", "year", "month"],
        },
    }

    logger.info("[VALIDATION] Validasi Star Schema...")
    for table, df in transformed.items():
        rule = rules.get(table, {})
        validate_dataframe(
            df, table,
            min_rows=rule.get("min_rows", 1),
            max_null_pct=0.20,
            required_cols=rule.get("required_cols"),
        )

    # Cek referential integrity: fact_orders.customer_id ⊆ dim_customers.customer_id
    fact = transformed.get("fact_orders")
    dim_c = transformed.get("dim_customers")
    if fact is not None and dim_c is not None:
        orphan_customers = set(fact["customer_id"]) - set(dim_c["customer_id"])
        orphan_pct = len(orphan_customers) / fact["customer_id"].nunique()
        if orphan_pct > 0.05:
            logger.warning(
                f"[VALIDATION WARNING] {orphan_pct:.1%} customer_id di fact_orders "
                f"tidak ada di dim_customers"
            )
        else:
            logger.info(f"[VALIDATION OK] Referential integrity customer_id: OK")

    logger.info("[VALIDATION] Star Schema LULUS validasi ✅")
