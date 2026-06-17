"""
dags/ecommerce_retrain.py
==========================
Airflow DAG — Auto Retrain Pipeline (Drift-Triggered)

Strategi:
  - Dibaca oleh sensor yang mengecek file sinyal dari DriftMonitor
  - Bila file 'data/retrain_signal.flag' ada → trigger retrain
  - Setelah retrain selesai → hapus flag

Alur:
  check_drift_signal → run_retrain → clear_signal

Jadwal:
  @hourly (sensor) — atau trigger manual dari DriftMonitor

"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator

logger = logging.getLogger(__name__)

DATA_DIR         = Path("/opt/airflow/data")
RETRAIN_FLAG     = DATA_DIR / "retrain_signal.flag"
MODEL_DIR        = Path("/opt/airflow/models")
PROCESSED_DIR    = DATA_DIR / "processed"
FIG_DIR          = Path("/opt/airflow/reports/figures")


# ── TASK FUNCTIONS ────────────────────────────────────────────────────────────

def check_drift_signal(**context) -> bool:
    """
    ShortCircuit: hanya lanjut jika file sinyal retrain ada.
    Jika tidak ada → skip seluruh downstream task (hemat resource).
    """
    flag_exists = RETRAIN_FLAG.exists()
    if flag_exists:
        import json
        with open(RETRAIN_FLAG, "r") as f:
            payload = json.load(f)
        logger.info(f"[retrain_dag] Retrain signal detected: {payload}")
    else:
        logger.info("[retrain_dag] No retrain signal. Skipping pipeline.")
    return flag_exists


def run_retrain(**context) -> None:
    """
    Task Utama: Jalankan ulang ML pipeline penuh.
    Sama dengan 'python src/back_end/pipelines/run_all.py' tapi dari Airflow.
    """
    sys.path.insert(0, "/opt/airflow")
    import joblib

    from src.back_end.ml.data_loader  import get_engine, load_orders, load_full
    from src.back_end.ml.features     import build_all_features
    from src.back_end.ml.segmentation import run_kmeans
    from src.back_end.ml.churn        import train_churn_model, predict_churn_risk

    logger.info("[retrain_dag] Starting retraining pipeline ...")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load
    engine      = get_engine()
    orders      = load_orders(engine)
    orders_full = load_full(engine)

    # 2. Feature Engineering
    rfm = build_all_features(orders, orders_full, churn_threshold=90)
    rfm.to_csv(PROCESSED_DIR / "rfm_data.csv", index=False)

    # 3. Segmentation
    rfm, kmeans, scaler = run_kmeans(rfm, n_clusters=4)

    # 4. Churn Model Training (auto-logs to MLflow)
    churn_model, metrics = train_churn_model(
        rfm, output_dir=str(FIG_DIR), compare_models=True
    )
    rfm = predict_churn_risk(churn_model, rfm)
    rfm.to_csv(PROCESSED_DIR / "customer_scores.csv", index=False)

    # 5. Save Updated Models
    joblib.dump(churn_model, MODEL_DIR / "churn_model.pkl")
    joblib.dump(kmeans,      MODEL_DIR / "kmeans_model.pkl")
    joblib.dump(scaler,      MODEL_DIR / "scaler.pkl")

    logger.info(
        f"[retrain_dag] ✅ Retrain complete | "
        f"Best: {metrics['best_model_name']} | AUC: {metrics['auc']:.4f}"
    )


def clear_retrain_signal(**context) -> None:
    """Bersihkan file flag setelah retrain selesai."""
    if RETRAIN_FLAG.exists():
        RETRAIN_FLAG.unlink()
        logger.info("[retrain_dag] Retrain signal cleared ✓")
    else:
        logger.info("[retrain_dag] No signal to clear")


def update_drift_baseline(**context) -> None:
    """
    Optional final step: update baseline statistik ke data terbaru
    agar future drift checks menggunakan distribusi ter-update.
    """
    sys.path.insert(0, "/opt/airflow")
    import pandas as pd
    from src.back_end.ml.monitoring.drift_monitor import DriftMonitor

    scores_path = PROCESSED_DIR / "customer_scores.csv"
    if not scores_path.exists():
        logger.warning("[retrain_dag] customer_scores.csv not found. Skipping baseline update.")
        return

    rfm = pd.read_csv(scores_path)
    monitor = DriftMonitor()
    monitor.set_baseline(rfm)
    logger.info("[retrain_dag] Drift baseline updated from retrained data ✓")


# ── DAG DEFINITION ────────────────────────────────────────────────────────────

default_args = {
    "owner":            "rizqi",
    "depends_on_past":  False,
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          1,
    "retry_delay":      timedelta(minutes=10),
}

with DAG(
    dag_id="ecommerce_auto_retrain",
    description=(
        "Auto Retrain DAG — triggered by DriftMonitor signal. "
        "Runs full ML pipeline and updates model artifacts."
    ),
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="@hourly",    # Sensor check setiap jam
    catchup=False,
    tags=["mlops", "retrain", "drift", "ecommerce"],
) as dag:

    check_signal = ShortCircuitOperator(
        task_id="check_drift_signal",
        python_callable=check_drift_signal,
        doc_md="**Sensor**: Cek file `data/retrain_signal.flag`. Short-circuit bila tidak ada.",
    )

    retrain = PythonOperator(
        task_id="run_retrain",
        python_callable=run_retrain,
        doc_md="**Retrain**: Jalankan ulang pipeline ML lengkap dan log metrics ke MLflow.",
    )

    clear_signal = PythonOperator(
        task_id="clear_retrain_signal",
        python_callable=clear_retrain_signal,
        doc_md="**Cleanup**: Hapus file flag sinyal setelah retrain berhasil.",
    )

    update_baseline = PythonOperator(
        task_id="update_drift_baseline",
        python_callable=update_drift_baseline,
        doc_md="**Baseline Update**: Update statistik baseline drift ke distribusi data terbaru.",
    )

    # DAG Chain: Sensor → Retrain → Clear → Update Baseline
    check_signal >> retrain >> clear_signal >> update_baseline
