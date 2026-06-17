from fastapi import APIRouter
from src.back_end.api.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/insights", tags=["Advanced Analytics"])

@router.get("/date-bounds")
def get_insights_date_bounds():
    """Mendapatkan tanggal awal dan akhir transaksi di database."""
    from src.back_end.ml.data_loader import get_engine
    from sqlalchemy import text
    try:
        engine = get_engine()
        with engine.connect() as conn:
            res = conn.execute(text("SELECT MIN(order_date)::date, MAX(order_date)::date FROM fact_orders"))
            row = res.fetchone()
            if row and row[0] and row[1]:
                return {"min_date": str(row[0]), "max_date": str(row[1])}
    except Exception as e:
        print(f"[API] Error getting date bounds: {e}")
    return {"min_date": "2022-01-01", "max_date": "2024-12-31"}

@router.get("/kpis")
def get_insights_kpis(d_from: str, d_to: str, segments: str = None):
    return AnalyticsService.get_kpis(d_from, d_to, segments)

@router.get("/trend")
def get_insights_trend(d_from: str, d_to: str, granularity: str = "Monthly", segments: str = None):
    return AnalyticsService.get_trend(d_from, d_to, granularity, segments)

@router.get("/status")
def get_insights_status(d_from: str, d_to: str, segments: str = None):
    return AnalyticsService.get_status_breakdown(d_from, d_to, segments)

@router.get("/products")
def get_insights_products(d_from: str, d_to: str, limit: int = 25, segments: str = None):
    return AnalyticsService.get_products(d_from, d_to, limit, segments)

@router.get("/categories")
def get_insights_categories(d_from: str, d_to: str, segments: str = None):
    return AnalyticsService.get_categories(d_from, d_to, segments)

@router.get("/rfm")
def get_insights_rfm(d_from: str, d_to: str, segments: str = None):
    return AnalyticsService.get_rfm_distribution(d_from, d_to, segments)

@router.get("/segment-categories")
def get_segment_categories(d_from: str, d_to: str, segments: str = None):
    return AnalyticsService.get_segment_categories(d_from, d_to, segments)
