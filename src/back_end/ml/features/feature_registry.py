"""
src/back_end/ml/features/feature_registry.py
=============================================
Feature Store Registry — Versioning & Reproducibility

Menyimpan:
  - feature_config.yaml  : konfigurasi pipeline fitur (threshold, windows, dll)
  - Versi output folder  : features_v{N}/ untuk reproducibility

Usage:
    config = load_feature_config()
    out_path = get_versioned_output_path(base_dir)
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Default config — digunakan bila YAML tidak tersedia
_DEFAULT_CONFIG = {
    "version": "v1",
    "churn_threshold_days": 90,
    "rfm_windows": [30, 60],
    "lag_periods": [1, 2, 3],
    "snapshot_date": None,           # None = auto (max of order_date)
    "feature_columns": [
        "frequency", "monetary", "avg_order_value",
        "avg_days_between_orders", "purchase_trend",
        "orders_last_90d", "orders_prev_90d",
        "unique_categories", "unique_products",
        "spend_last_30d", "spend_last_60d", "spend_velocity",
        "days_since_first_order",
    ],
    "created_at": None,
}

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH   = _PROJECT_ROOT / "data" / "feature_config.json"


def load_feature_config() -> dict:
    """
    Load feature config dari file JSON.
    Jika tidak ada, gunakan default config dan simpan ke disk.

    Returns:
        dict konfigurasi feature pipeline
    """
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info(f"[feature_registry] Config loaded from {CONFIG_PATH}")
        return config

    # First-time: tulis default config
    default = _DEFAULT_CONFIG.copy()
    default["created_at"] = datetime.utcnow().isoformat()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(default, f, indent=2)
    logger.info(f"[feature_registry] Default config written to {CONFIG_PATH}")
    return default


def save_feature_config(config: dict) -> None:
    """Simpan konfigurasi yang sudah dimodifikasi kembali ke disk."""
    config["updated_at"] = datetime.utcnow().isoformat()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    logger.info(f"[feature_registry] Config saved → {CONFIG_PATH}")


def get_versioned_output_path(base_dir: str, version: str = None) -> str:
    """
    Kembalikan path output yang di-versioning secara otomatis.

    Contoh output:
        data/processed/features_v1/
        data/processed/features_v2/

    Args:
        base_dir : direktori dasar (contoh: "data/processed")
        version  : string versi; jika None, increment otomatis

    Returns:
        str path ke folder versioned features
    """
    if version is None:
        config = load_feature_config()
        version = config.get("version", "v1")

    versioned_path = os.path.join(base_dir, f"features_{version}")
    os.makedirs(versioned_path, exist_ok=True)

    # Simpan metadata versi
    meta = {
        "version": version,
        "path": versioned_path,
        "created_at": datetime.utcnow().isoformat(),
    }
    meta_path = os.path.join(versioned_path, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"[feature_registry] Versioned output path: {versioned_path}")
    return versioned_path


def bump_version(config: dict) -> dict:
    """
    Increment versi config (v1 → v2 → v3 ...).

    Args:
        config: dict konfigurasi saat ini
    Returns:
        config dengan versi baru
    """
    current = config.get("version", "v1")
    try:
        num = int(current.lstrip("v")) + 1
    except ValueError:
        num = 2
    config["version"] = f"v{num}"
    config["bumped_at"] = datetime.utcnow().isoformat()
    save_feature_config(config)
    logger.info(f"[feature_registry] Version bumped: {current} → {config['version']}")
    return config
