"""
src/back_end/ml/features/user_features.py
==========================================
User & Product Diversity Features — Customer Intelligence Feature Store

Features:
  Product Diversity:
    - unique_categories : jumlah kategori berbeda yang dibeli
    - unique_products   : jumlah produk unik yang dibeli
    - last_category     : kategori terakhir yang dibeli
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def add_product_features(
    rfm: pd.DataFrame,
    orders_full: pd.DataFrame,
) -> pd.DataFrame:
    """
    Tambah fitur berbasis PRODUCT DIVERSITY per customer.
    Memerlukan orders_full yang sudah di-join dengan dim_products.

    Args:
        rfm         : DataFrame dari create_rfm()
        orders_full : hasil load_full() — harus ada kolom 'category', 'product_id'
    """
    need_cols = ["customer_id", "category", "product_id"]
    available = [c for c in need_cols if c in orders_full.columns]

    if len(available) < 3:
        logger.warning(
            f"[user_features] orders_full missing columns: {set(need_cols) - set(available)}. "
            "Skipping product diversity features."
        )
        return rfm

    prod = (
        orders_full.groupby("customer_id")
        .agg(
            unique_categories =("category",   "nunique"),
            unique_products   =("product_id", "nunique"),
        )
        .reset_index()
    )

    # Last category bought
    if "order_date" in orders_full.columns:
        last_cat = (
            orders_full
            .sort_values("order_date")
            .groupby("customer_id")["category"]
            .last()
            .reset_index()
            .rename(columns={"category": "last_category"})
        )
        prod = prod.merge(last_cat, on="customer_id", how="left")

    rfm = rfm.merge(prod, on="customer_id", how="left")
    rfm["unique_categories"] = rfm["unique_categories"].fillna(1).astype(int)
    rfm["unique_products"]   = rfm["unique_products"].fillna(1).astype(int)

    logger.info("[user_features] Product diversity features added")
    return rfm


def add_channel_features(
    rfm: pd.DataFrame,
    orders_full: pd.DataFrame,
) -> pd.DataFrame:
    """
    Tambah fitur berbasis TRAFFIC CHANNEL per customer.
    Requires orders_full dengan kolom 'traffic_source'.

    Args:
        rfm         : DataFrame RFM existing
        orders_full : Result of load_full() with 'traffic_source' column
    """
    if "traffic_source" not in orders_full.columns:
        logger.warning("[user_features] traffic_source not found. Skipping channel features.")
        return rfm

    channel = (
        orders_full.groupby("customer_id")["traffic_source"]
        .agg(lambda x: x.mode().iloc[0] if len(x) > 0 else "Unknown")
        .reset_index()
        .rename(columns={"traffic_source": "primary_channel"})
    )

    rfm = rfm.merge(channel, on="customer_id", how="left")
    rfm["primary_channel"] = rfm["primary_channel"].fillna("Unknown")

    logger.info("[user_features] Channel features added")
    return rfm
