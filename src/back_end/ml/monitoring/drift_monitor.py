"""
src/back_end/ml/monitoring/drift_monitor.py
============================================
Data & Model Drift Monitor — Customer Intelligence System

Kemampuan:
  1. Menghitung statistik deskriptif distribusi fitur (mean, std, min, max)
  2. Mendeteksi drift jika distribusi menyimpang > N standard deviations dari baseline
  3. Menyimpan snapshot statistik ke log JSON untuk audit trail
  4. Mengirimkan sinyal (via file flag) untuk memicu Auto Retrain Airflow DAG

Dependencies:
  - evidently (opsional, recommended):
    pip install "evidently>=0.4.0"
  - Tanpa evidently: pakai implementasi statistik bawaan (numpy/scipy)

Usage:
    from src.back_end.ml.monitoring.drift_monitor import DriftMonitor

    monitor = DriftMonitor("data/processed/baseline_stats.json")
    drift_report = monitor.check_drift(current_rfm_df)
    if drift_report["drift_detected"]:
        monitor.trigger_retrain_signal()
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Kolom yang dipantau drift-nya
MONITORED_FEATURES = [
    "recency", "frequency", "monetary", "avg_order_value",
    "avg_days_between_orders", "purchase_trend",
    "orders_last_90d", "unique_categories",
]

# Path sinyal retrain — dibaca oleh Airflow DAG
_PROJECT_ROOT     = Path(__file__).resolve().parents[5]
RETRAIN_FLAG_PATH = _PROJECT_ROOT / "data" / "retrain_signal.flag"
DRIFT_LOG_PATH    = _PROJECT_ROOT / "models" / "logs" / "drift_log.json"


class DriftMonitor:
    """
    Memantau distribusi fitur dan mendeteksi data drift.

    Args:
        baseline_path : path ke file JSON statistik baseline
        threshold_std : jumlah std deviation sebagai batas drift (default: 3)
    """

    def __init__(self, baseline_path: str = None, threshold_std: float = 3.0):
        self.threshold_std = threshold_std
        self.baseline_path = baseline_path or str(
            _PROJECT_ROOT / "data" / "baseline_stats.json"
        )
        self.baseline: dict = {}
        self._load_baseline()

    # ── Baseline ──────────────────────────────────────────────────────────────

    def _load_baseline(self) -> None:
        """Load baseline stats dari JSON jika tersedia."""
        if os.path.exists(self.baseline_path):
            with open(self.baseline_path, "r", encoding="utf-8") as f:
                self.baseline = json.load(f)
            logger.info(f"[DriftMonitor] Baseline loaded from {self.baseline_path}")
        else:
            logger.info("[DriftMonitor] No baseline found. Run set_baseline() terlebih dahulu.")

    def set_baseline(self, df: pd.DataFrame) -> dict:
        """
        Simpan statistik distribusi data saat ini sebagai baseline referensi.

        Args:
            df: DataFrame RFM (biasanya hasil run pertama pipeline)
        Returns:
            dict statistik baseline
        """
        stats = self._compute_stats(df)
        stats["set_at"] = datetime.utcnow().isoformat()
        os.makedirs(os.path.dirname(self.baseline_path), exist_ok=True)
        with open(self.baseline_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        self.baseline = stats
        logger.info(f"[DriftMonitor] Baseline set from {len(df):,} records → {self.baseline_path}")
        return stats

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _compute_stats(self, df: pd.DataFrame) -> dict:
        """Kalkulasi statistik deskriptif untuk semua MONITORED_FEATURES."""
        stats = {}
        for col in MONITORED_FEATURES:
            if col not in df.columns:
                continue
            series = df[col].dropna()
            stats[col] = {
                "mean":   float(series.mean()),
                "std":    float(series.std()),
                "min":    float(series.min()),
                "max":    float(series.max()),
                "median": float(series.median()),
                "count":  int(len(series)),
            }
        return stats

    # ── Drift Detection ───────────────────────────────────────────────────────

    def check_drift(self, current_df: pd.DataFrame) -> dict:
        """
        Bandingkan distribusi DataFrame saat ini terhadap baseline.

        Returns:
            dict hasil analisis drift:
                {
                  "drift_detected": bool,
                  "drifted_features": list,
                  "feature_drift": {feature: {"z_score": ..., "drifted": bool}}
                }
        """
        if not self.baseline:
            logger.warning("[DriftMonitor] No baseline set. Auto-setting baseline from current data.")
            self.set_baseline(current_df)
            return {"drift_detected": False, "drifted_features": [], "feature_drift": {}}

        current_stats = self._compute_stats(current_df)
        feature_drift = {}
        drifted = []

        for feat, cur in current_stats.items():
            if feat not in self.baseline:
                continue
            base = self.baseline[feat]
            base_std = base.get("std", 0)
            if base_std == 0:
                continue
            z_score = abs(cur["mean"] - base["mean"]) / base_std
            is_drifted = z_score > self.threshold_std
            feature_drift[feat] = {
                "baseline_mean": round(base["mean"], 4),
                "current_mean":  round(cur["mean"], 4),
                "z_score":       round(z_score, 4),
                "drifted":       is_drifted,
            }
            if is_drifted:
                drifted.append(feat)
                logger.warning(
                    f"[DriftMonitor] 🔴 DRIFT DETECTED in '{feat}': "
                    f"z_score={z_score:.2f} (threshold={self.threshold_std})"
                )

        drift_detected = len(drifted) > 0
        report = {
            "drift_detected":   drift_detected,
            "drifted_features": drifted,
            "feature_drift":    feature_drift,
            "checked_at":       datetime.utcnow().isoformat(),
            "threshold_std":    self.threshold_std,
        }

        self._save_drift_log(report)

        if drift_detected:
            logger.warning(
                f"[DriftMonitor] ⚠️  DRIFT in {len(drifted)} feature(s): {drifted}"
            )
        else:
            logger.info("[DriftMonitor] ✅ No drift detected")

        return report

    # ── Auto Retrain Signal ───────────────────────────────────────────────────

    def trigger_retrain_signal(self, report: dict = None) -> None:
        """
        Tulis file flag sinyal retrain yang akan dibaca oleh Airflow DAG
        (dags/ecommerce_retrain.py).

        File: data/retrain_signal.flag
        """
        RETRAIN_FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "triggered_at": datetime.utcnow().isoformat(),
            "reason": "data_drift",
            "drifted_features": report.get("drifted_features", []) if report else [],
        }
        with open(RETRAIN_FLAG_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"[DriftMonitor] 🚀 Retrain signal written → {RETRAIN_FLAG_PATH}")

    @staticmethod
    def clear_retrain_signal() -> None:
        """Hapus flag sinyal setelah retrain selesai."""
        if RETRAIN_FLAG_PATH.exists():
            RETRAIN_FLAG_PATH.unlink()
            logger.info("[DriftMonitor] Retrain signal cleared")

    @staticmethod
    def has_retrain_signal() -> bool:
        """Cek apakah retrain signal aktif (untuk Airflow DAG sensor)."""
        return RETRAIN_FLAG_PATH.exists()

    # ── Evidently Integration (Opsional) ─────────────────────────────────────

    def run_evidently_report(self, reference_df: pd.DataFrame, current_df: pd.DataFrame,
                              output_dir: str = None) -> None:
        """
        Generate Evidently HTML drift report (opsional — hanya bila evidently terinstall).

        Install: pip install "evidently>=0.4.0"
        """
        try:
            from evidently.report import Report
            from evidently.metric_preset import DataDriftPreset

            report = Report(metrics=[DataDriftPreset()])
            report.run(reference_data=reference_df, current_data=current_df)

            out = output_dir or str(_PROJECT_ROOT / "reports")
            os.makedirs(out, exist_ok=True)
            report_path = os.path.join(out, "evidently_drift_report.html")
            report.save_html(report_path)
            logger.info(f"[DriftMonitor] Evidently report → {report_path}")
        except ImportError:
            logger.warning("[DriftMonitor] evidently not installed. Skipping HTML report.\n"
                           "Install with: pip install 'evidently>=0.4.0'")

    # ── Log ───────────────────────────────────────────────────────────────────

    def _save_drift_log(self, report: dict) -> None:
        """Append drift report ke drift_log.json untuk audit trail."""
        DRIFT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        logs = []
        if DRIFT_LOG_PATH.exists():
            try:
                with open(DRIFT_LOG_PATH, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                logs = []
        logs.append(report)
        with open(DRIFT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)


# ── CLI untuk testing manual ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(_PROJECT_ROOT))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    from src.back_end.ml.data_loader import get_engine, load_orders
    from src.back_end.ml.features import build_all_features

    engine = get_engine()
    orders = load_orders(engine)
    rfm    = build_all_features(orders, orders)

    monitor = DriftMonitor()
    monitor.set_baseline(rfm)

    # Simulasi drift: inject noise
    rfm_noisy = rfm.copy()
    rfm_noisy["recency"]  = rfm_noisy["recency"] * 5
    rfm_noisy["monetary"] = rfm_noisy["monetary"] / 10

    drift_report = monitor.check_drift(rfm_noisy)
    if drift_report["drift_detected"]:
        monitor.trigger_retrain_signal(drift_report)
