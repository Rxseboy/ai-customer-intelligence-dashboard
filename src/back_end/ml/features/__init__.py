"""
src/back_end/ml/features/__init__.py
=====================================
Feature Store Package — Customer Intelligence System

Re-exposes semua fungsi publik agar import lama tetap berjalan:
    from src.back_end.ml.features import build_all_features, create_rfm, ...
"""

from .rfm_features import (
    create_rfm,
    add_behavioral_features,
    create_churn_label,
    build_rfm_features,
)
from .user_features import add_product_features
from .time_series_features import add_time_series_features
from .feature_registry import load_feature_config, get_versioned_output_path

# Backward-compatible master builder
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def build_all_features(
    orders: pd.DataFrame,
    orders_full: pd.DataFrame,
    churn_threshold: int = 90,
) -> pd.DataFrame:
    """
    Master feature builder — backward-compatible entry point.

    Calls all sub-feature modules in the correct pipeline order.
    Output version is stored via feature_registry.

    Returns:
        rfm DataFrame dengan semua features + churn label
    """
    config = load_feature_config()
    churn_threshold = config.get("churn_threshold_days", churn_threshold)

    rfm = create_rfm(orders)
    rfm = add_behavioral_features(rfm, orders)
    rfm = add_product_features(rfm, orders_full)
    rfm = add_time_series_features(rfm, orders)
    rfm = create_churn_label(rfm, days_threshold=churn_threshold)

    feature_cols = [
        c for c in rfm.columns
        if c not in ["customer_id", "churn", "last_order", "last_category"]
    ]
    logger.info(f"[FeatureStore] Total features: {len(feature_cols)}")
    logger.info(f"[FeatureStore] Columns: {feature_cols}")
    return rfm
