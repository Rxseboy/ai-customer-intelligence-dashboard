"""
api/main.py
FastAPI — Customer Intelligence System
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.back_end.api.services.model_cache import ModelCache

# Import Routers
from src.back_end.api.routers import health, predictions, analytics, rag, monitoring, customers

_model_cache = ModelCache()

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    limiter = Limiter(key_func=get_remote_address)
    _RATE_LIMIT_AVAILABLE = True
except ImportError:
    limiter = None
    _RATE_LIMIT_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: warm up caches on startup so the first
    API call does not block waiting for model/RFM data to load.
    """
    try:
        _model_cache.get_rfm()
        print("[API] \u2705 RFM cache loaded")
    except Exception as e:
        print(f"[API] \u26a0\ufe0f  RFM cache load failed: {e}")

    try:
        _model_cache.get_rag_assistant()
        print("[API] \u2705 RAG assistant initialized")
    except Exception as e:
        print(f"[API] \u26a0\ufe0f  RAG init failed: {e}")
    yield


app = FastAPI(
    title="Customer Intelligence System API",
    description="""
## \U0001f6d2 E-Commerce Customer Intelligence System \u2014 Production API

### Capabilities
- **Churn Prediction** \u2014 XGBoost model
- **Customer Segmentation** \u2014 RFM-based clustering
- **AI Insight Assistant** \u2014 Natural language querying (RAG)
- **Drift Monitoring** \u2014 Data distribution health status
- **Product Analytics** \u2014 Revenue, category, and brand breakdowns
    """,
    version="3.0.0",
    contact={"name": "Rizqi Fajar", "email": "rizqyfajar99@gmail.com"},
    lifespan=lifespan,
)

if _RATE_LIMIT_AVAILABLE:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*", "X-API-Key", "Content-Type", "Accept", "Authorization"],
    expose_headers=["X-API-Key"],
)

# Prometheus metrics are disabled to prevent routing conflicts with newer FastAPI versions
# try:
#     from prometheus_fastapi_instrumentator import Instrumentator
#     Instrumentator().instrument(app).expose(app)
# except ImportError:
#     print("[API] prometheus-fastapi-instrumentator not installed, metrics disabled.")

# Register Routers
app.include_router(health.router)
app.include_router(predictions.router)
app.include_router(analytics.router)
app.include_router(rag.router)
app.include_router(monitoring.router)
app.include_router(customers.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "E-Commerce Customer Intelligence System API v3.0",
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[API] Starting Customer Intelligence API on http://{host}:{port}")
    uvicorn.run(
        "src.back_end.api.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
