"""
src/back_end/ml/clv.py
======================
Model Customer Lifetime Value (CLV) menggunakan Lifetimes.
  - BG/NBD: Memprediksi jumlah pembelian mendatang (frequency).
  - Gamma-Gamma: Memprediksi average monetary value per order.

Catatan serialisasi:
  lifetimes BetaGeoFitter menyimpan internal lambda setelah .fit(),
  sehingga joblib.dump gagal. Solusi: gunakan cloudpickle (bundled
  bersama MLflow), dan tambahan fallback simpan params ke JSON.
"""

import os
import json
import logging
import numpy as np
import pandas as pd

# MLflow
try:
    import mlflow
    _MLFLOW_AVAILABLE = True
except ImportError:
    _MLFLOW_AVAILABLE = False

# cloudpickle (biasanya tersedia karena MLflow)
try:
    import cloudpickle as _pickle_mod
    _CLOUDPICKLE = True
except ImportError:
    import pickle as _pickle_mod
    _CLOUDPICKLE = False

# Lifetimes
try:
    from lifetimes.utils import summary_data_from_transaction_data
    from lifetimes import BetaGeoFitter, GammaGammaFitter
    _LIFETIMES_AVAILABLE = True
except ImportError:
    _LIFETIMES_AVAILABLE = False

logger = logging.getLogger(__name__)


# ── Helpers: save & load (menghindari lambda pickle bug lifetimes) ────────────

def _save_model(model, path: str) -> None:
    """
    Simpan fitter ke file.
    Prioritas: cloudpickle → params JSON (fallback).
    """
    try:
        with open(path, "wb") as f:
            _pickle_mod.dump(model, f)
        logger.info(f"[clv] Saved (cloudpickle={_CLOUDPICKLE}): {path}")
    except Exception as e:
        # Fallback: simpan hanya params sebagai JSON
        logger.warning(f"[clv] pickle gagal ({e}), fallback → params JSON")
        params_path = path.replace(".pkl", "_params.json")
        params = {k: float(v) for k, v in model.params_.items()}
        with open(params_path, "w") as f:
            json.dump({"params_": params, "penalizer_coef": float(model.penalizer_coef)}, f)
        logger.info(f"[clv] Params saved → {params_path}")


def _load_model(path: str, fitter_class):
    """
    Muat fitter dari file (cloudpickle / params JSON).
    """
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return _pickle_mod.load(f)
        except Exception:
            pass

    # Coba load dari params JSON
    params_path = path.replace(".pkl", "_params.json")
    if os.path.exists(params_path):
        with open(params_path) as f:
            data = json.load(f)
        model = fitter_class(penalizer_coef=data["penalizer_coef"])
        model.params_ = pd.Series(data["params_"])
        return model

    raise FileNotFoundError(f"Model tidak ditemukan: {path} (atau {params_path})")


# ── Data Preparation ──────────────────────────────────────────────────────────

def prepare_clv_data(orders: pd.DataFrame) -> pd.DataFrame:
    """Build RFM summary data expected by lifetimes."""
    if not _LIFETIMES_AVAILABLE:
        raise ImportError("pip install lifetimes>=0.11.3 required for CLV.")

    df = orders[["customer_id", "order_date", "sale_price"]].copy()
    df["order_date"] = pd.to_datetime(df["order_date"]).dt.date

    summary = summary_data_from_transaction_data(
        transactions=df,
        customer_id_col="customer_id",
        datetime_col="order_date",
        monetary_value_col="sale_price",
        observation_period_end=df["order_date"].max()
    )
    logger.info(f"[clv] Disiapkan summary (shape: {summary.shape})")
    return summary


# ── Training ──────────────────────────────────────────────────────────────────

def train_clv_models(orders: pd.DataFrame, output_dir: str = "models", track_mlflow: bool = True):
    """
    Train BG/NBD + Gamma-Gamma dengan auto-retry penalizer naik jika gagal konvergen.
    Menggunakan cloudpickle untuk serialisasi (menghindari lambda pickle bug).
    """
    os.makedirs(output_dir, exist_ok=True)
    summary = prepare_clv_data(orders)

    # ── BG/NBD ───────────────────────────────────────────────────────────────
    bgf = None
    for _pen in [0.01, 0.1, 0.5, 1.0]:
        try:
            _bgf = BetaGeoFitter(penalizer_coef=_pen)
            _bgf.fit(summary["frequency"], summary["recency"], summary["T"])
            bgf = _bgf
            logger.info(f"[clv] BG/NBD konvergen (penalizer={_pen})")
            break
        except Exception as _e:
            logger.warning(f"[clv] BG/NBD penalizer={_pen} gagal: {_e}")
    if bgf is None:
        raise RuntimeError("BG/NBD tidak dapat konvergen.")

    # ── Gamma-Gamma ───────────────────────────────────────────────────────────
    # Filter: hanya repeat buyer, monetary > 0, buang outlier ekstrem
    returning = summary[
        (summary["frequency"] > 0) & (summary["monetary_value"] > 0)
    ].copy()
    upper = returning["monetary_value"].quantile(0.999)
    returning = returning[returning["monetary_value"] <= upper]

    ggf = None
    for _pen in [0.01, 0.1, 0.5, 1.0]:
        try:
            _ggf = GammaGammaFitter(penalizer_coef=_pen)
            _ggf.fit(returning["frequency"], returning["monetary_value"])
            ggf = _ggf
            logger.info(f"[clv] Gamma-Gamma konvergen (penalizer={_pen}, n={len(returning):,})")
            break
        except Exception as _e:
            logger.warning(f"[clv] Gamma-Gamma penalizer={_pen} gagal: {_e}")
    if ggf is None:
        raise RuntimeError("Gamma-Gamma tidak dapat konvergen.")

    # ── Save ──────────────────────────────────────────────────────────────────
    _save_model(bgf, os.path.join(output_dir, "clv_bgf_model.pkl"))
    _save_model(ggf, os.path.join(output_dir, "clv_ggf_model.pkl"))

    if _MLFLOW_AVAILABLE and track_mlflow:
        _log_clv_metrics(bgf, ggf, summary)

    return bgf, ggf, summary


def load_clv_models(model_dir: str = "models"):
    """Muat CLV models dari disk."""
    bgf = _load_model(os.path.join(model_dir, "clv_bgf_model.pkl"), BetaGeoFitter)
    ggf = _load_model(os.path.join(model_dir, "clv_ggf_model.pkl"), GammaGammaFitter)
    return bgf, ggf


# ── MLflow Logging ────────────────────────────────────────────────────────────

def _log_clv_metrics(bgf, ggf, summary):
    try:
        mlflow.set_experiment("customer-clv")
        with mlflow.start_run(run_name="bg_gg"):
            mlflow.log_params({k: float(v) for k, v in bgf.params_.items()})
            mlflow.log_metrics({"training_size": len(summary)})
            logger.info("[clv] Traced to MLFlow")
    except Exception as e:
        logger.warning(f"[clv] MLflow log gagal: {e}")


# ── Inference ─────────────────────────────────────────────────────────────────

def predict_clv(summary_df: pd.DataFrame, bgf, ggf, months: int = 1) -> pd.DataFrame:
    """Scoring customer CLV."""
    df = summary_df.copy()
    t = months * 30

    df["predicted_purchases"] = bgf.predict(t, df["frequency"], df["recency"], df["T"])

    # Hanya customer dg frequency > 0 yang bisa diberi prediksi GGF
    df["predicted_aov"] = np.where(
        df["frequency"] > 0,
        ggf.conditional_expected_average_profit(df["frequency"], df["monetary_value"]),
        0.0,
    )

    df["clv_pred"] = ggf.customer_lifetime_value(
        bgf,
        df["frequency"],
        df["recency"],
        df["T"],
        df["monetary_value"],
        time=months,
        discount_rate=0.01,
    )
    df["clv_pred"] = df["clv_pred"].fillna(0)
    df["predicted_aov"] = df["predicted_aov"].fillna(0)
    return df


if __name__ == "__main__":
    from src.back_end.ml.data_loader import get_engine, load_orders
    logging.basicConfig(level=logging.INFO)
    eng = get_engine()
    orders = load_orders(eng)
    bgf, ggf, sumdf = train_clv_models(orders)
    scored = predict_clv(sumdf, bgf, ggf, months=1)
    print(scored.sort_values("clv_pred", ascending=False).head())
