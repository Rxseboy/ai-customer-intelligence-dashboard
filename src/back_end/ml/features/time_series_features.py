"""
src/back_end/ml/features/time_series_features.py
==================================================
Time Series Features — Customer Intelligence Feature Store

Features:
  Rolling window aggregations:
    - spend_last_30d    : total spend 30 hari terakhir
    - spend_last_60d    : total spend 60 hari terakhir
    - orders_last_30d   : order count 30 hari terakhir
    - days_since_first_order : umur customer

  Velocity:
    - spend_velocity    : spend_last_30d / avg_order_value
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def add_time_series_features(
    rfm: pd.DataFrame,
    orders: pd.DataFrame,
    snapshot_date=None,
    windows: list = [30, 60],
) -> pd.DataFrame:
    """
    Tambah fitur time window & spend velocity per customer.

    Args:
        rfm          : DataFrame dari build_rfm_features()
        orders       : fact_orders dengan kolom order_date + sale_price
        snapshot_date: tanggal referensi (default: max order_date)
        windows      : list window hari untuk rolling aggregation
    """
    orders = orders.copy()
    orders["order_date"] = pd.to_datetime(orders["order_date"])

    if snapshot_date is None:
        snapshot_date = orders["order_date"].max()

    result = rfm.copy()

    # ── Rolling window spend + order count ──────────────────────────────────
    for w in windows:
        cutoff = snapshot_date - pd.Timedelta(days=w)
        window_orders = orders[orders["order_date"] >= cutoff]

        spend_agg = (
            window_orders.groupby("customer_id")["sale_price"]
            .sum()
            .rename(f"spend_last_{w}d")
        )
        order_agg = (
            window_orders.groupby("customer_id")["order_id"]
            .nunique()
            .rename(f"orders_last_{w}d")
        )

        result = result.merge(spend_agg, on="customer_id", how="left")
        result = result.merge(order_agg, on="customer_id", how="left")
        result[f"spend_last_{w}d"]  = result[f"spend_last_{w}d"].fillna(0.0)
        result[f"orders_last_{w}d"] = result[f"orders_last_{w}d"].fillna(0).astype(int)

    # ── Days since first order (customer age) ────────────────────────────────
    first_order = (
        orders.groupby("customer_id")["order_date"]
        .min()
        .reset_index()
        .rename(columns={"order_date": "first_order_date"})
    )
    result = result.merge(first_order, on="customer_id", how="left")
    result["days_since_first_order"] = (
        snapshot_date - pd.to_datetime(result["first_order_date"])
    ).dt.days.fillna(0).astype(int)
    result = result.drop(columns=["first_order_date"], errors="ignore")

    # ── Spend velocity ────────────────────────────────────────────────────────
    result["spend_velocity"] = (
        result["spend_last_30d"] / result["avg_order_value"].clip(lower=1)
    ).fillna(0.0)

    logger.info(f"[time_series_features] Window features added: {[f'spend_last_{w}d' for w in windows]}")
    return result


def add_lag_features(
    rfm: pd.DataFrame,
    orders: pd.DataFrame,
    lag_periods: list = [1, 2, 3],
) -> pd.DataFrame:
    """
    Tambah lag features berbasis urutan pembelian per customer.
    Berguna untuk model forecasting / CLV.

    Args:
        rfm         : DataFrame RFM
        orders      : fact_orders
        lag_periods : lag dalam unit 'order ke-n'
    """
    orders = orders.copy()
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders_sorted = orders.sort_values(["customer_id", "order_date"])

    for lag in lag_periods:
        lag_col = f"monetary_lag_{lag}"
        lag_values = (
            orders_sorted.groupby("customer_id")["sale_price"]
            .shift(lag)
        )
        lag_df = (
            orders_sorted.assign(**{lag_col: lag_values})
            .groupby("customer_id")[lag_col]
            .last()
            .reset_index()
        )
        rfm = rfm.merge(lag_df, on="customer_id", how="left")
        rfm[lag_col] = rfm[lag_col].fillna(0.0)

    logger.info(f"[time_series_features] Lag features added: {[f'monetary_lag_{l}' for l in lag_periods]}")
    return rfm
