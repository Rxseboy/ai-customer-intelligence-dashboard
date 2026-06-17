"""
src/back_end/api/services/model_cache.py
=========================================
Centralized model loading and caching service.

Previously, all global state (_churn_model, _rfm_cache, _rag_assistant,
_clv_bgf_model, _clv_ggf_model) was scattered across api/main.py as
module-level globals with inline loading functions.

This module extracts all of that into a single, importable service class
with thread-safe lazy loading. All routers import from here — no more
global state in main.py.

Usage:
    from src.back_end.api.services.model_cache import ModelCache
    cache = ModelCache()
    model = cache.get_churn_model()
    rfm   = cache.get_rfm()
    rag   = cache.get_rag_assistant()
"""

import os
import threading
import logging
import joblib
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

MODEL_PATH   = os.path.join(PROJECT_ROOT, "models", "churn_model.pkl")
CLV_BGF_PATH = os.path.join(PROJECT_ROOT, "models", "clv_bgf_model.pkl")
CLV_GGF_PATH = os.path.join(PROJECT_ROOT, "models", "clv_ggf_model.pkl")
SCORES_PATH  = os.path.join(PROJECT_ROOT, "data", "processed", "customer_scores.csv")

DRIFT_LOG_PATH = os.path.join(PROJECT_ROOT, "models", "logs", "drift_log.json")
RETRAIN_FLAG   = os.path.join(PROJECT_ROOT, "data", "retrain_signal.flag")
BASELINE_PATH  = os.path.join(PROJECT_ROOT, "data", "baseline_stats.json")


class ModelCache:
    """
    Thread-safe singleton service for lazy-loading and caching ML models.

    All cached objects are loaded on first access and reused on subsequent calls.
    Supports MLflow Registry → local .pkl fallback for churn and CLV models.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton: always return the same instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._rfm_cache: Optional[pd.DataFrame] = None
        self._churn_model = None
        self._rag_assistant = None
        self._clv_bgf_model = None
        self._clv_ggf_model = None
        self._rfm_lock = threading.Lock()
        self._churn_lock = threading.Lock()
        self._rag_lock = threading.Lock()
        self._clv_lock = threading.Lock()
        self._initialized = True

    # ── RFM Cache ──────────────────────────────────────────────────────────────

    def get_rfm(self) -> pd.DataFrame:
        """Load or compute RFM/customer scores. Returns cached DataFrame."""
        with self._rfm_lock:
            if self._rfm_cache is not None:
                return self._rfm_cache

            if os.path.exists(SCORES_PATH):
                self._rfm_cache = pd.read_csv(SCORES_PATH)
                logger.info(f"[ModelCache] RFM loaded from CSV: {len(self._rfm_cache):,} rows")
                return self._rfm_cache

            # Compute from live DB
            try:
                from src.back_end.ml.data_loader import get_engine, load_orders
                from src.back_end.ml.features import create_rfm, create_churn_label
                engine = get_engine()
                df = load_orders(engine)
                rfm = create_rfm(df)
                rfm = create_churn_label(rfm)
                self._rfm_cache = rfm
                logger.info(f"[ModelCache] RFM computed from DB: {len(rfm):,} rows")
            except Exception as e:
                logger.error(f"[ModelCache] RFM load/compute failed: {e}")
                self._rfm_cache = pd.DataFrame()

            return self._rfm_cache

    def invalidate_rfm(self):
        """Force recompute on next get_rfm() call."""
        with self._rfm_lock:
            self._rfm_cache = None
            logger.info("[ModelCache] RFM cache invalidated")

    # ── Churn Model ────────────────────────────────────────────────────────────

    def get_churn_model(self):
        """Load churn model from MLflow Registry or local .pkl fallback."""
        with self._churn_lock:
            if self._churn_model is not None:
                return self._churn_model

            # Try MLflow first
            try:
                import mlflow.pyfunc
                tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
                if tracking_uri:
                    mlflow.set_tracking_uri(tracking_uri)
                    pyfunc_model = mlflow.pyfunc.load_model("models:/churn_model/Production")
                    if hasattr(pyfunc_model, "unwrap_python_model"):
                        self._churn_model = pyfunc_model.unwrap_python_model()
                    elif hasattr(pyfunc_model, "_model_impl"):
                        self._churn_model = pyfunc_model._model_impl
                    else:
                        self._churn_model = pyfunc_model
                    logger.info("[ModelCache] Churn model loaded from MLflow Registry")
                    return self._churn_model
            except Exception as e:
                logger.warning(f"[ModelCache] MLflow churn load failed, using local: {e}")

            # Fallback: local joblib
            if os.path.exists(MODEL_PATH):
                try:
                    self._churn_model = joblib.load(MODEL_PATH)
                    logger.info("[ModelCache] Churn model loaded from local disk")
                    return self._churn_model
                except Exception as e:
                    logger.error(f"[ModelCache] Local churn model load failed: {e}")

            logger.warning("[ModelCache] No churn model available — using recency fallback")
            return None

    # ── CLV Models ─────────────────────────────────────────────────────────────

    def get_clv_models(self):
        """Load BG/NBD and Gamma-Gamma CLV models. Returns (bgf, ggf) tuple."""
        with self._clv_lock:
            if self._clv_bgf_model is not None and self._clv_ggf_model is not None:
                return self._clv_bgf_model, self._clv_ggf_model

            # Try MLflow
            try:
                import mlflow.pyfunc
                tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
                if tracking_uri:
                    mlflow.set_tracking_uri(tracking_uri)

                    def _unwrap(m):
                        if hasattr(m, "unwrap_python_model"):
                            return m.unwrap_python_model()
                        return getattr(m, "_model_impl", m)

                    self._clv_bgf_model = _unwrap(mlflow.pyfunc.load_model("models:/clv_bgf_model/Production"))
                    self._clv_ggf_model = _unwrap(mlflow.pyfunc.load_model("models:/clv_ggf_model/Production"))
                    logger.info("[ModelCache] CLV models loaded from MLflow Registry")
                    return self._clv_bgf_model, self._clv_ggf_model
            except Exception as e:
                logger.warning(f"[ModelCache] MLflow CLV load failed, using local: {e}")

            # Fallback: local joblib
            try:
                if os.path.exists(CLV_BGF_PATH) and os.path.exists(CLV_GGF_PATH):
                    self._clv_bgf_model = joblib.load(CLV_BGF_PATH)
                    self._clv_ggf_model = joblib.load(CLV_GGF_PATH)
                    logger.info("[ModelCache] CLV models loaded from local disk")
                    return self._clv_bgf_model, self._clv_ggf_model
            except Exception as e:
                logger.error(f"[ModelCache] Local CLV model load failed: {e}")

            return None, None

    # ── RAG Assistant ──────────────────────────────────────────────────────────

    def get_rag_assistant(self):
        """Lazy-load RAG assistant singleton."""
        with self._rag_lock:
            if self._rag_assistant is not None:
                return self._rag_assistant
            try:
                from src.back_end.ml.rag import RAGInsightAssistant
                self._rag_assistant = RAGInsightAssistant()
                logger.info("[ModelCache] RAG assistant initialized")
            except Exception as e:
                logger.error(f"[ModelCache] RAG init failed: {e}")
                self._rag_assistant = None
            return self._rag_assistant

    # ── Health / Status ────────────────────────────────────────────────────────

    def model_ready(self) -> bool:
        """True if churn model file exists on disk."""
        return os.path.exists(MODEL_PATH)

    def data_ready(self) -> bool:
        """True if pre-computed customer scores exist on disk."""
        return os.path.exists(SCORES_PATH)


# Module-level singleton for convenience imports
_cache = ModelCache()
get_rfm = _cache.get_rfm
get_churn_model = _cache.get_churn_model
get_clv_models = _cache.get_clv_models
get_rag_assistant = _cache.get_rag_assistant
