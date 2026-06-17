"""
models/churn.py
===============
Churn Prediction Model — Customer Intelligence System

Model Comparison:
  - Baseline  : Logistic Regression
  - Advanced  : XGBoost

PENTING — Anti-leakage:
  'recency' TIDAK digunakan sebagai feature.
  Model belajar dari behavioral patterns (frequency, avg_order_value,
  purchase_trend, unique_categories, dll.) bukan dari recency yang
  langsung berkorelasi dengan churn label (recency > 90d).
"""

import os
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.linear_model  import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline      import Pipeline
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    ConfusionMatrixDisplay, roc_curve, accuracy_score,
    precision_score, recall_score, f1_score
)
from xgboost import XGBClassifier

# ── MLflow Experiment Tracking ────────────────────────────────────────────────
try:
    import mlflow
    import mlflow.sklearn
    import mlflow.xgboost
    _MLFLOW_AVAILABLE = True
except ImportError:
    _MLFLOW_AVAILABLE = False

logger = logging.getLogger(__name__)

MLFLOW_EXPERIMENT = "customer-churn-prediction"

# ── FEATURE SET (NO RECENCY — prevents data leakage) ─────────────────────────
CHURN_FEATURES = [
    "frequency",
    "monetary",
    "avg_order_value",
    "avg_days_between_orders",
    "purchase_trend",
    "orders_last_90d",
    "orders_prev_90d",
    "unique_categories",
    "unique_products",
]


def _select_features(rfm: pd.DataFrame) -> list:
    """Return only CHURN_FEATURES that actually exist in rfm."""
    available = [f for f in CHURN_FEATURES if f in rfm.columns]
    if len(available) < 3:
        logger.warning(f"[churn] Only {len(available)} features available. Minimum 3 needed.")
    logger.info(f"[churn] Features used: {available}")
    return available


def train_churn_model(
    rfm: pd.DataFrame,
    output_dir: str = "outputs",
    compare_models: bool = True,
):
    """
    Train churn prediction models dengan model comparison.

    Args:
        rfm           : DataFrame dengan features + 'churn' label
        output_dir    : folder untuk simpan plots
        compare_models: jika True, jalankan Logistic Regression sebagai baseline

    Returns:
        best_model : model dengan AUC tertinggi
        metrics    : dict hasil evaluasi lengkap
    """
    os.makedirs(output_dir, exist_ok=True)
    feat_cols = _select_features(rfm)

    X = rfm[feat_cols].fillna(0)
    y = rfm["churn"]

    logger.info(f"[churn] Dataset: {len(rfm):,} rows | "
                f"churn=0: {(y==0).sum():,} | churn=1: {(y==1).sum():,}")
    logger.info(f"[churn] Churn rate: {y.mean()*100:.1f}%")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    results = {}

    # ── Model 1: Logistic Regression (Baseline) ───────────────────────────────
    if compare_models:
        logger.info("[churn] Training Logistic Regression (baseline)...")
        lr_pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(
                class_weight="balanced",
                max_iter=1000,
                random_state=42,
            ))
        ])
        lr_pipe.fit(X_train, y_train)
        lr_pred  = lr_pipe.predict(X_test)
        lr_proba = lr_pipe.predict_proba(X_test)[:, 1]
        lr_auc   = roc_auc_score(y_test, lr_proba)
        lr_cv    = cross_val_score(lr_pipe, X, y, cv=cv, scoring="roc_auc")

        results["Logistic Regression"] = {
            "model":     lr_pipe,
            "auc":       lr_auc,
            "cv_auc":    lr_cv.mean(),
            "accuracy":  accuracy_score(y_test, lr_pred),
            "precision": precision_score(y_test, lr_pred, zero_division=0),
            "recall":    recall_score(y_test, lr_pred, zero_division=0),
            "f1":        f1_score(y_test, lr_pred, zero_division=0),
            "y_pred":    lr_pred,
            "y_proba":   lr_proba,
        }
        logger.info(f"  Logistic Regression — AUC: {lr_auc:.4f} | CV: {lr_cv.mean():.4f}")

    # ── Model 2: XGBoost (Advanced) ───────────────────────────────────────────
    logger.info("[churn] Training XGBoost (advanced)...")
    pos_weight = max(1.0, (y == 0).sum() / (y == 1).sum())
    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=pos_weight,
        random_state=42,
        eval_metric="logloss",
        verbosity=0,
    )
    xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    xgb_pred  = xgb.predict(X_test)
    xgb_proba = xgb.predict_proba(X_test)[:, 1]
    xgb_auc   = roc_auc_score(y_test, xgb_proba)
    xgb_cv    = cross_val_score(xgb, X, y, cv=cv, scoring="roc_auc")

    results["XGBoost"] = {
        "model":     xgb,
        "auc":       xgb_auc,
        "cv_auc":    xgb_cv.mean(),
        "accuracy":  accuracy_score(y_test, xgb_pred),
        "precision": precision_score(y_test, xgb_pred, zero_division=0),
        "recall":    recall_score(y_test, xgb_pred, zero_division=0),
        "f1":        f1_score(y_test, xgb_pred, zero_division=0),
        "y_pred":    xgb_pred,
        "y_proba":   xgb_proba,
        "feature_importances": dict(zip(feat_cols, xgb.feature_importances_)),
    }
    logger.info(f"  XGBoost — AUC: {xgb_auc:.4f} | CV: {xgb_cv.mean():.4f}")

    # ── Model Comparison Table ────────────────────────────────────────────────
    _print_comparison_table(results)

    # ── Select Best Model ─────────────────────────────────────────────────────
    best_name  = max(results, key=lambda k: results[k]["cv_auc"])
    best       = results[best_name]
    best_model = best["model"]
    logger.info(f"[churn] Best model: {best_name} (CV AUC: {best['cv_auc']:.4f})")

    # ── Plots ─────────────────────────────────────────────────────────────────
    _plot_roc_comparison(results, y_test, output_dir)
    _plot_confusion(y_test, best["y_pred"], output_dir)
    if "feature_importances" in results["XGBoost"]:
        _plot_feature_importance(results["XGBoost"]["feature_importances"], output_dir)

    metrics = {
        "best_model_name":  best_name,
        "auc":              best["auc"],
        "cv_auc":           best["cv_auc"],
        "accuracy":         best["accuracy"],
        "precision":        best["precision"],
        "recall":           best["recall"],
        "f1":               best["f1"],
        "features":         feat_cols,
        "all_results":      {
            name: {k: v for k, v in r.items() if k not in ["model","y_pred","y_proba"]}
            for name, r in results.items()
        },
        "report": classification_report(y_test, best["y_pred"], output_dict=True),
    }

    # ── MLflow Tracking ───────────────────────────────────────────────────────
    _log_to_mlflow(best_name, best_model, metrics, feat_cols, output_dir)

    return best_model, metrics


def _log_to_mlflow(model_name: str, model, metrics: dict, feat_cols: list, output_dir: str) -> None:
    """Log experiment ke MLflow. Gracefully skip bila MLflow tidak tersedia."""
    if not _MLFLOW_AVAILABLE:
        logger.warning("[churn] MLflow not installed. Skipping experiment tracking.\n"
                       "Install with: pip install mlflow>=2.0.0")
        _log_metrics_json(metrics, output_dir)
        return

    try:
        mlflow.set_experiment(MLFLOW_EXPERIMENT)
        with mlflow.start_run(run_name=f"churn_{model_name.lower().replace(' ', '_')}"):
            # Params
            mlflow.log_params({
                "model_name":      model_name,
                "features":        ",".join(feat_cols),
                "n_features":      len(feat_cols),
            })
            # Metrics
            mlflow.log_metrics({
                "auc":             metrics["auc"],
                "cv_auc":          metrics["cv_auc"],
                "accuracy":        metrics["accuracy"],
                "precision":       metrics["precision"],
                "recall":          metrics["recall"],
                "f1":              metrics["f1"],
            })
            # Artifacts: plots
            for fname in ["roc_comparison.png", "confusion_matrix.png", "feature_importance.png"]:
                fpath = os.path.join(output_dir, fname)
                if os.path.exists(fpath):
                    mlflow.log_artifact(fpath, artifact_path="plots")
            # Model artifact
            if model_name == "XGBoost":
                mlflow.xgboost.log_model(model, artifact_path="model")
            else:
                mlflow.sklearn.log_model(model, artifact_path="model")
        logger.info(f"[churn] MLflow run logged: experiment='{MLFLOW_EXPERIMENT}'")
    except Exception as exc:
        logger.warning(f"[churn] MLflow logging failed: {exc}")
        _log_metrics_json(metrics, output_dir)


def _log_metrics_json(metrics: dict, output_dir: str) -> None:
    """Fallback: simpan metrics ke JSON bila MLflow tidak tersedia."""
    import json
    from datetime import datetime
    safe = {k: v for k, v in metrics.items() if k not in ["all_results", "report", "features"]}
    safe["logged_at"] = datetime.utcnow().isoformat()
    log_path = os.path.join(output_dir, "experiment_log.json")
    # Append ke file JSON (list of runs)
    runs = []
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                runs = json.load(f)
        except Exception:
            runs = []
    runs.append(safe)
    with open(log_path, "w") as f:
        json.dump(runs, f, indent=2)
    logger.info(f"[churn] Metrics (fallback) saved → {log_path}")


def _print_comparison_table(results: dict) -> None:
    """Print model comparison table ke log."""
    logger.info("\n" + "=" * 65)
    logger.info("  MODEL COMPARISON")
    logger.info("=" * 65)
    header = f"  {'Model':<25} {'AUC':>7} {'CV AUC':>8} {'Acc':>7} {'Prec':>7} {'Rec':>7} {'F1':>7}"
    logger.info(header)
    logger.info("  " + "-" * 63)
    for name, r in results.items():
        row = (
            f"  {name:<25} "
            f"{r['auc']:>7.4f} {r['cv_auc']:>8.4f} "
            f"{r['accuracy']:>7.4f} {r['precision']:>7.4f} "
            f"{r['recall']:>7.4f} {r['f1']:>7.4f}"
        )
        logger.info(row)
    logger.info("=" * 65)


def _plot_roc_comparison(results: dict, y_test, output_dir: str) -> None:
    """ROC curves untuk semua model dalam satu plot."""
    colors = {"Logistic Regression": "#F77F00", "XGBoost": "#00B4D8"}
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor("#0D1117")
    ax.set_facecolor("#161B22")

    for name, r in results.items():
        fpr, tpr, _ = roc_curve(y_test, r["y_proba"])
        ax.plot(fpr, tpr, lw=2, color=colors.get(name, "#8B949E"),
                label=f"{name} (AUC={r['auc']:.3f})")

    ax.plot([0, 1], [0, 1], "--", color="#21262D", lw=1)
    ax.set_xlabel("False Positive Rate", color="#E6EDF3")
    ax.set_ylabel("True Positive Rate", color="#E6EDF3")
    ax.set_title("ROC Curve — Model Comparison", color="#E6EDF3", fontsize=13)
    ax.tick_params(colors="#8B949E")
    ax.legend(facecolor="#21262D", labelcolor="#E6EDF3")
    for sp in ax.spines.values():
        sp.set_color("#21262D")

    path = os.path.join(output_dir, "roc_comparison.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0D1117")
    plt.close()
    logger.info(f"[churn] ROC comparison → {path}")


def _plot_confusion(y_test, y_pred, output_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(5, 4))
    fig.patch.set_facecolor("#0D1117")
    ax.set_facecolor("#161B22")
    cm   = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(cm, display_labels=["Retained", "Churned"])
    disp.plot(ax=ax, colorbar=False, cmap="Blues")
    ax.set_title("Confusion Matrix (Best Model)", color="#E6EDF3")
    ax.tick_params(colors="#E6EDF3")
    path = os.path.join(output_dir, "confusion_matrix.png")
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0D1117")
    plt.close()
    logger.info(f"[churn] Confusion matrix → {path}")


def _plot_feature_importance(importances: dict, output_dir: str) -> None:
    feat = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    names, vals = zip(*feat)
    colors = ["#00B4D8", "#7B2FBE", "#F77F00", "#06D6A0", "#EF233C",
              "#8B949E", "#FFB703", "#219EBC", "#FB8500"][:len(names)]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("#0D1117")
    ax.set_facecolor("#161B22")
    bars = ax.barh(names, vals, color=colors)
    ax.set_xlabel("Importance Score", color="#E6EDF3")
    ax.set_title("XGBoost Feature Importance — Churn Model", color="#E6EDF3", fontsize=13)
    ax.tick_params(colors="#E6EDF3")
    for sp in ax.spines.values():
        sp.set_color("#21262D")
    for bar, val in zip(bars, vals):
        ax.text(val + 0.002, bar.get_y() + bar.get_height()/2,
                f"{val:.3f}", va="center", color="#E6EDF3", fontsize=9)

    plt.tight_layout()
    path = os.path.join(output_dir, "feature_importance.png")
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0D1117")
    plt.close()
    logger.info(f"[churn] Feature importance → {path}")


def predict_churn_risk(model, rfm: pd.DataFrame) -> pd.DataFrame:
    """
    Tambah kolom churn_probability dan risk_level ke RFM DataFrame.

    Args:
        model : fitted model (sklearn Pipeline atau XGBClassifier)
        rfm   : DataFrame dengan feature columns
    """
    feat_cols = _select_features(rfm)
    X = rfm[feat_cols].fillna(0)
    rfm = rfm.copy()
    rfm["churn_probability"] = model.predict_proba(X)[:, 1]
    rfm["risk_level"] = pd.cut(
        rfm["churn_probability"],
        bins=[0, 0.3, 0.6, 1.0],
        labels=["Low", "Medium", "High"],
        include_lowest=True,
    )
    return rfm


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.back_end.ml.data_loader import get_engine, load_orders, load_full
    from src.back_end.ml.features    import build_all_features
    eng  = get_engine()
    df   = load_orders(eng)
    full = load_full(eng)
    rfm  = build_all_features(df, full, churn_threshold=90)
    model, metrics = train_churn_model(rfm)
    logger.info(f"Best: {metrics['best_model_name']} | AUC: {metrics['auc']:.4f}")
