import os
from datetime import datetime
from fastapi import APIRouter
from src.back_end.api.schemas.contracts import HealthResponse
from src.back_end.api.services.model_cache import ModelCache

router = APIRouter(tags=["Health"])
_model_cache = ModelCache()

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "churn_model.pkl")

@router.get("/health", response_model=HealthResponse)
def health():
    """Health check lengkap: model, data, MLflow, dan cache status."""
    model_ready = os.path.exists(MODEL_PATH)
    data_ready  = os.path.exists(
        os.path.join(PROJECT_ROOT, "data", "processed", "customer_scores.csv")
    )

    mlflow_ready = False
    try:
        import mlflow
        mlflow_ready = True
    except ImportError:
        pass

    rag = _model_cache.get_rag_assistant()
    cache_stats = rag.cache_stats() if rag else None

    return HealthResponse(
        status="healthy",
        model_ready=model_ready,
        data_ready=data_ready,
        mlflow_ready=mlflow_ready,
        timestamp=datetime.utcnow().isoformat(),
        cache_stats=cache_stats,
    )
