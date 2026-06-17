"""
src/back_end/ml/features/rfm_features.py
==========================================
RFM Feature Engineering — Customer Intelligence Feature Store

Features:
  Basic RFM:
    - recency           : hari sejak order terakhir
    - frequency         : jumlah order unik
    - monetary          : total spend
    - avg_order_value   : rata-rata nilai order

  Behavioral (tidak bocor ke label churn):
    - avg_days_between_orders
    - purchase_trend          : orders_last_90d - orders_prev_90d
    - orders_last_90d
    - orders_prev_90d

  Label:
    - churn: 1 jika recency > threshold
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def create_rfm(df: pd.DataFrame, snapshot_date=None) -> pd.DataFrame:
    """
    Buat tabel RFM dasar dari fact_orders.

    Returns:
        DataFrame dengan kolom: customer_id, recency, frequency, monetary, avg_order_value
    """
    df = df.copy()
    df["order_date"] = pd.to_datetime(df["order_date"])

    if snapshot_date is None:
        snapshot_date = df["order_date"].max()

    rfm = (
        df.groupby("customer_id")
        .agg(
            last_order  =("order_date", "max"),
            recency     =("order_date", lambda x: (snapshot_date - x.max()).days),
            frequency   =("order_id",   "nunique"),
            monetary    =("sale_price", "sum"),
        )
        .reset_index()
    )

    rfm["avg_order_value"] = rfm["monetary"] / rfm["frequency"].clip(lower=1)

    logger.info(f"[rfm_features] RFM dibuat: {len(rfm):,} customers")
    logger.info(
        f"[rfm_features] Recency  — mean: {rfm['recency'].mean():.0f}d, "
        f"median: {rfm['recency'].median():.0f}d"
    )
    logger.info(
        f"[rfm_features] Monetary — mean: ${rfm['monetary'].mean():.0f}, "
        f"median: ${rfm['monetary'].median():.0f}"
    )
    return rfm


def add_behavioral_features(
    rfm: pd.DataFrame,
    orders: pd.DataFrame,
    snapshot_date=None,
) -> pd.DataFrame:
    """
    Tambah fitur berbasis TIME PATTERN per customer.
    Fitur ini TIDAK leak ke churn label.

    Args:
        rfm         : DataFrame dari create_rfm()
        orders      : fact_orders (order_id, customer_id, order_date, sale_price)
        snapshot_date: tanggal referensi (default: max order_date)
    """
    orders = orders.copy()
    orders["order_date"] = pd.to_datetime(orders["order_date"])

    if snapshot_date is None:
        snapshot_date = orders["order_date"].max()

    # ── Avg days between consecutive orders (VECTORIZED) ────────────────────
    orders_sorted = orders.sort_values(["customer_id", "order_date"]).copy()
    orders_sorted["_gap"] = (
        orders_sorted
        .groupby("customer_id")["order_date"]
        .diff()
        .dt.days
    )
    gap_df = (
        orders_sorted
        .groupby("customer_id")["_gap"]
        .mean()
        .reset_index()
        .rename(columns={"_gap": "avg_days_between_orders"})
    )

    # ── Purchase trend: last 90d vs prev 90d ────────────────────────────────
    cutoff_recent = snapshot_date - pd.Timedelta(days=90)
    cutoff_prev   = snapshot_date - pd.Timedelta(days=180)

    recent = (
        orders[orders["order_date"] >= cutoff_recent]
        .groupby("customer_id")["order_id"].nunique()
        .rename("orders_last_90d")
    )
    prev = (
        orders[
            (orders["order_date"] >= cutoff_prev) &
            (orders["order_date"] < cutoff_recent)
        ]
        .groupby("customer_id")["order_id"].nunique()
        .rename("orders_prev_90d")
    )

    rfm = (
        rfm
        .merge(gap_df, on="customer_id", how="left")
        .merge(recent,  on="customer_id", how="left")
        .merge(prev,    on="customer_id", how="left")
    )

    rfm["orders_last_90d"]  = rfm["orders_last_90d"].fillna(0).astype(int)
    rfm["orders_prev_90d"]  = rfm["orders_prev_90d"].fillna(0).astype(int)
    rfm["purchase_trend"]   = rfm["orders_last_90d"] - rfm["orders_prev_90d"]
    rfm["avg_days_between_orders"] = rfm["avg_days_between_orders"].fillna(
        rfm["avg_days_between_orders"].median()
    )

    logger.info("[rfm_features] Behavioral features added")
    return rfm


def create_churn_label(rfm: pd.DataFrame, days_threshold: int = 90) -> pd.DataFrame:
    """
    Tambahkan label churn ke RFM.
    Threshold default = 90 hari, di tas leakage 30 hari.

    Args:
        days_threshold: customer dianggap churn jika recency > days_threshold
    """
    rfm = rfm.copy()
    rfm["churn"] = (rfm["recency"] > days_threshold).astype(int)
    churn_rate   = rfm["churn"].mean() * 100
    logger.info(
        f"[rfm_features] Churn label (>{days_threshold}d): "
        f"{churn_rate:.1f}% churn | {100-churn_rate:.1f}% retained"
    )
    return rfm


def build_rfm_features(
    orders: pd.DataFrame,
    churn_threshold: int = 90,
) -> pd.DataFrame:
    """Convenience builder: RFM + behavioral + label."""
    rfm = create_rfm(orders)
    rfm = add_behavioral_features(rfm, orders)
    rfm = create_churn_label(rfm, days_threshold=churn_threshold)
    return rfm
