"""
routers/customers.py
Endpoint untuk data customer — mendukung tampilan "Top Customers" di frontend.
"""

from fastapi import APIRouter, Depends, Query
from src.back_end.api.dependencies import get_api_key
from src.back_end.api.services.model_cache import ModelCache

router = APIRouter(prefix="/customers", tags=["Customers"])
_model_cache = ModelCache()


@router.get("/top")
def get_top_customers(
    limit: int = Query(default=10, ge=1, le=100),
):
    """
    Return the top N customers ranked by total monetary value (revenue).
    Data is pulled from the in-memory RFM cache computed from the database.
    No authentication required for this public analytics endpoint.
    """
    rfm = _model_cache.get_rfm()

    if rfm is None or rfm.empty:
        return {"customers": [], "total": 0}

    needed_cols = {"customer_id", "recency", "frequency", "monetary", "segment"}
    available = needed_cols.intersection(set(rfm.columns))
    df = rfm[list(available)].copy()

    if "monetary" in df.columns:
        df = df.sort_values("monetary", ascending=False)

    top = df.head(limit)

    customers = []
    for _, row in top.iterrows():
        entry: dict = {}
        for col in available:
            val = row[col]
            # Convert numpy types to Python native for JSON serialisation
            try:
                if hasattr(val, "item"):
                    val = val.item()
            except Exception:
                val = str(val)
            entry[col] = val
        customers.append(entry)

    return {"customers": customers, "total": len(customers)}
