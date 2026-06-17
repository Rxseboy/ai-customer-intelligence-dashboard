"""
transform.py
============
Module untuk membersihkan data (Clean) dan membentuk Star Schema.

Star Schema yang dihasilkan:
  - fact_orders         → Tabel fakta transaksi utama
  - dim_customers       → Dimensi pelanggan
  - dim_products        → Dimensi produk
  - dim_date            → Dimensi waktu/tanggal
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ==============================================================================
# SECTION 1: CLEANING FUNCTIONS
# ==============================================================================

def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Membersihkan tabel orders."""
    logger.info("  Membersihkan tabel orders...")
    before = len(df)

    df = df.drop_duplicates(subset=["order_id"])
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["returned_at"] = pd.to_datetime(df["returned_at"], errors="coerce")
    df["shipped_at"] = pd.to_datetime(df["shipped_at"], errors="coerce")
    df["delivered_at"] = pd.to_datetime(df["delivered_at"], errors="coerce")

    # Hapus order yang dibatalkan
    df = df[df["status"] != "Cancelled"].copy()

    # Hapus baris dengan order_id atau user_id kosong
    df = df.dropna(subset=["order_id", "user_id"])

    logger.info(f"    {before:,} → {len(df):,} baris (hapus {before - len(df):,} baris)")
    return df


def clean_order_items(df: pd.DataFrame) -> pd.DataFrame:
    """Membersihkan tabel order_items."""
    logger.info("  Membersihkan tabel order_items...")
    before = len(df)

    df = df.drop_duplicates(subset=["id"])
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["shipped_at"] = pd.to_datetime(df["shipped_at"], errors="coerce")
    df["delivered_at"] = pd.to_datetime(df["delivered_at"], errors="coerce")
    df["returned_at"] = pd.to_datetime(df["returned_at"], errors="coerce")

    # Harga tidak boleh negatif
    df = df[df["sale_price"] >= 0].copy()
    df = df.dropna(subset=["order_id", "user_id", "product_id", "sale_price"])

    logger.info(f"    {before:,} → {len(df):,} baris (hapus {before - len(df):,} baris)")
    return df


def clean_users(df: pd.DataFrame) -> pd.DataFrame:
    """Membersihkan tabel users."""
    logger.info("  Membersihkan tabel users...")
    before = len(df)

    df = df.drop_duplicates(subset=["id"])
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df = df.dropna(subset=["id", "first_name", "last_name", "email"])

    # Normalisasi gender
    df["gender"] = df["gender"].str.strip().str.title().fillna("Unknown")

    # Normalisasi negara
    df["country"] = df["country"].str.strip().str.upper().fillna("UNKNOWN")

    logger.info(f"    {before:,} → {len(df):,} baris (hapus {before - len(df):,} baris)")
    return df


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    """Membersihkan tabel products."""
    logger.info("  Membersihkan tabel products...")
    before = len(df)

    df = df.drop_duplicates(subset=["id"])
    df = df.dropna(subset=["id", "name", "category"])

    # Harga tidak boleh negatif
    df["retail_price"] = pd.to_numeric(df["retail_price"], errors="coerce")
    df["cost"] = pd.to_numeric(df["cost"], errors="coerce")
    df = df[df["retail_price"] >= 0].copy()

    # Normalisasi teks
    df["category"] = df["category"].str.strip().str.title()
    df["brand"] = df["brand"].str.strip().str.title().fillna("Unknown Brand")
    df["department"] = df["department"].str.strip().str.title().fillna("Unknown")

    logger.info(f"    {before:,} → {len(df):,} baris (hapus {before - len(df):,} baris)")
    return df


# ==============================================================================
# SECTION 2: STAR SCHEMA BUILDER
# ==============================================================================

def build_dim_customers(users: pd.DataFrame) -> pd.DataFrame:
    """
    Membangun dim_customers dari tabel users.

    Kolom output:
        customer_id, first_name, last_name, email, gender,
        age, city, state, country, created_at
    """
    logger.info("  Membangun dim_customers...")

    cols = [
        "id", "first_name", "last_name", "email",
        "gender", "age", "city", "state", "country", "created_at"
    ]
    # Pilih kolom yang ada
    available = [c for c in cols if c in users.columns]
    dim = users[available].copy()
    dim = dim.rename(columns={"id": "customer_id"})

    logger.info(f"    ✅ dim_customers: {len(dim):,} baris")
    return dim


def build_dim_products(products: pd.DataFrame) -> pd.DataFrame:
    """
    Membangun dim_products dari tabel products.

    Kolom output:
        product_id, name, category, brand, department,
        retail_price, cost
    """
    logger.info("  Membangun dim_products...")

    cols = [
        "id", "name", "category", "brand",
        "department", "retail_price", "cost"
    ]
    available = [c for c in cols if c in products.columns]
    dim = products[available].copy()
    dim = dim.rename(columns={"id": "product_id"})

    logger.info(f"    ✅ dim_products: {len(dim):,} baris")
    return dim


def build_dim_date(min_date: pd.Timestamp, max_date: pd.Timestamp) -> pd.DataFrame:
    """
    Membangun dim_date (kalender) dari rentang tanggal transaksi.

    Kolom output:
        date_id, full_date, year, quarter, month, month_name,
        week, day_of_week, day_name, is_weekend
    """
    logger.info("  Membangun dim_date...")

    date_range = pd.date_range(start=min_date.normalize(), end=max_date.normalize(), freq="D")
    dim = pd.DataFrame({"full_date": date_range})

    dim["date_id"]      = dim["full_date"].dt.strftime("%Y%m%d").astype(int)
    dim["year"]         = dim["full_date"].dt.year
    dim["quarter"]      = dim["full_date"].dt.quarter
    dim["month"]        = dim["full_date"].dt.month
    dim["month_name"]   = dim["full_date"].dt.strftime("%B")
    dim["week"]         = dim["full_date"].dt.isocalendar().week.astype(int)
    dim["day_of_week"]  = dim["full_date"].dt.dayofweek + 1   # 1=Monday
    dim["day_name"]     = dim["full_date"].dt.strftime("%A")
    dim["is_weekend"]   = dim["day_of_week"].isin([6, 7])

    logger.info(f"    ✅ dim_date: {len(dim):,} baris ({dim['year'].min()} – {dim['year'].max()})")
    return dim


def build_fact_orders(
    order_items: pd.DataFrame,
    orders: pd.DataFrame
) -> pd.DataFrame:
    """
    Membangun fact_orders dengan menggabungkan order_items + orders.

    Kolom output:
        fact_id, order_id, order_item_id, customer_id, product_id,
        date_id, order_date, sale_price, status
    """
    logger.info("  Membangun fact_orders...")

    # --- Siapkan order_items: rename kolom ambigu SEBELUM merge ---
    items = order_items.copy()
    # Rename 'id' -> 'order_item_id' sebelum merge agar tidak tabrakan
    if "id" in items.columns:
        items = items.rename(columns={"id": "order_item_id"})
    # Rename 'user_id' di order_items -> 'customer_id' langsung (sebelum merge)
    # sehingga tidak ada collision dengan user_id dari orders
    if "user_id" in items.columns:
        items = items.rename(columns={"user_id": "customer_id"})
    # Hapus kolom yang akan diambil dari orders supaya tidak collision
    for col in ["created_at", "status"]:
        if col in items.columns:
            items = items.drop(columns=[col])

    # --- Siapkan orders: hanya ambil kolom yang dibutuhkan ---
    orders_cols = [c for c in ["order_id", "created_at", "status"] if c in orders.columns]
    orders_slim = orders[orders_cols].copy()
    orders_slim = orders_slim.rename(columns={"created_at": "order_date"})

    # --- Merge: tidak ada lagi kolom duplikat ---
    fact = items.merge(orders_slim, on="order_id", how="left")

    # --- Buat date_id ---
    fact["order_date"] = pd.to_datetime(fact["order_date"], errors="coerce")
    fact["date_id"] = (
        fact["order_date"]
        .dt.strftime("%Y%m%d")
        .pipe(pd.to_numeric, errors="coerce")
        .astype("Int64")
    )

    # --- Margin = sale_price - cost (jika ada) ---
    if "cost" in fact.columns:
        fact["margin"] = fact["sale_price"] - fact["cost"]

    # --- Pilih kolom final ---
    final_cols = [
        "order_id", "order_item_id", "customer_id", "product_id",
        "date_id", "order_date", "sale_price", "status"
    ]
    if "margin" in fact.columns:
        final_cols.append("margin")

    available = [c for c in final_cols if c in fact.columns]
    fact = fact[available].copy()

    # --- Tambah surrogate key ---
    fact = fact.reset_index(drop=True)
    fact.insert(0, "fact_id", fact.index + 1)

    # --- Hapus baris krusial yang kosong ---
    fact = fact.dropna(subset=["order_id", "customer_id", "product_id", "sale_price"])

    logger.info(f"    ✅ fact_orders: {len(fact):,} baris")
    return fact


# ==============================================================================
# SECTION 3: ORCHESTRATOR
# ==============================================================================

def run_transform(raw: dict) -> dict:
    """
    Menjalankan seluruh proses Transform + Star Schema.

    Args:
        raw: Dictionary hasil extract_all_tables()

    Returns:
        Dictionary berisi semua tabel star schema
    """
    logger.info("=" * 50)
    logger.info("TAHAP TRANSFORM: Membersihkan & Membentuk Star Schema")
    logger.info("=" * 50)

    # --- STEP 1: CLEAN ---
    logger.info("\n[1/2] Cleaning data...")
    orders      = clean_orders(raw["orders"])
    order_items = clean_order_items(raw["order_items"])
    users       = clean_users(raw["users"])
    products    = clean_products(raw["products"])

    # --- STEP 2: BUILD STAR SCHEMA ---
    logger.info("\n[2/2] Membangun Star Schema...")

    dim_customers = build_dim_customers(users)
    dim_products  = build_dim_products(products)

    # Rentang tanggal dari order
    min_date = orders["created_at"].min()
    max_date = orders["created_at"].max()
    dim_date  = build_dim_date(min_date, max_date)

    fact_orders = build_fact_orders(order_items, orders)

    result = {
        "dim_customers": dim_customers,
        "dim_products":  dim_products,
        "dim_date":      dim_date,
        "fact_orders":   fact_orders,
    }

    logger.info("\nTransform selesai. Ringkasan:")
    for name, df in result.items():
        logger.info(f"  {name:<20} → {len(df):>8,} baris | {len(df.columns)} kolom")

    return result
