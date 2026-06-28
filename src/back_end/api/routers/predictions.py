import os
import pandas as pd
import numpy as np
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text

from src.back_end.api.schemas.contracts import (
    CustomerRFM, ChurnResponse, SegmentResponse,
    CLVResponse, RecommendationResponse
)
from src.back_end.api.dependencies import get_api_key
from src.back_end.api.services.model_cache import ModelCache
from src.back_end.ml.data_loader import get_engine

router = APIRouter(prefix="/predict", tags=["Predictions"], dependencies=[Depends(get_api_key)])
_model_cache = ModelCache()

# Project root path for model file discovery
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


@router.post("/churn", response_model=ChurnResponse)
def predict_churn(customer: CustomerRFM):
    """
    Predict churn probability for a single customer using RFM inputs.
    Falls back to a calibrated recency-based heuristic when no model is available.
    """
    model = _model_cache.get_churn_model()

    if model is None:
        # Calibrated heuristic: combine recency + frequency + monetary
        recency_score  = min(1.0, customer.recency / 180.0)          # 0–1: 180+ days = max risk
        freq_score     = max(0.0, 1.0 - customer.frequency / 20.0)   # high freq = low risk
        monetary_score = max(0.0, 1.0 - customer.monetary / 2000.0)  # high spend = low risk
        churn_prob = min(1.0, (recency_score * 0.6) + (freq_score * 0.25) + (monetary_score * 0.15))
    else:
        aov     = customer.avg_order_value or (customer.monetary / max(customer.frequency, 1))
        avg_days = 365 / max(customer.frequency, 1)
        decay   = max(0.0, 1.0 - (customer.recency / 365.0))

        expected_90d    = customer.frequency * (90.0 / 365.0)
        orders_last_90d  = max(0, int(round(expected_90d * decay)))
        orders_prev_90d  = max(0, int(round(expected_90d * min(1.0, 1.5 - decay))))
        purchase_trend   = orders_last_90d - orders_prev_90d

        # Build feature dict — include recency so model can use it if trained with it
        feature_values = {
            "recency":                 customer.recency,
            "frequency":               customer.frequency,
            "monetary":                customer.monetary,
            "avg_order_value":         aov,
            "avg_days_between_orders": avg_days,
            "purchase_trend":          purchase_trend,
            "orders_last_90d":         orders_last_90d,
            "orders_prev_90d":         orders_prev_90d,
            "unique_categories":       min(customer.frequency, 5),
            "unique_products":         min(customer.frequency, 10),
        }

        # Dynamically determine feature ordering from training module
        try:
            from src.back_end.ml.churn import CHURN_FEATURES
            model_features = CHURN_FEATURES
        except ImportError:
            model_features = list(feature_values.keys())

        feature_row = np.array([[feature_values.get(f, 0.0) for f in model_features]])
        raw_prob = float(model.predict_proba(feature_row)[0][1])

        # Blend model output with heuristic to prevent extreme calibration collapse
        recency_score = min(1.0, customer.recency / 180.0)
        freq_score    = max(0.0, 1.0 - customer.frequency / 20.0)
        heuristic     = min(1.0, (recency_score * 0.6) + (freq_score * 0.4))
        churn_prob    = (raw_prob * 0.7) + (heuristic * 0.3)

    # Risk classification thresholds
    if churn_prob >= 0.6:
        risk = "🔴 High"
        prediction = "CHURN"
        message = "Customer berisiko tinggi churn. Kirim promo re-engagement segera."
    elif churn_prob >= 0.3:
        risk = "🟡 Medium"
        prediction = "AT RISK"
        message = "Customer menunjukkan tanda-tanda penurunan. Monitor closely."
    else:
        risk = "🟢 Low"
        prediction = "RETAINED"
        message = "Customer aktif dan cenderung tetap loyal."

    return ChurnResponse(
        churn_probability=round(churn_prob, 4),
        risk_level=risk,
        prediction=prediction,
        recency_days=customer.recency,
        message=message,
    )



@router.post("/segment", response_model=SegmentResponse)
def predict_segment(customer: CustomerRFM):
    """
    Classify a single customer into an RFM segment using population quantiles.
    Requires the RFM cache to be populated; scores are derived from existing
    customer distribution rather than fixed breakpoints.
    """
    rfm = _model_cache.get_rfm()

    r_series = pd.Series([customer.recency] + rfm["recency"].tolist())
    f_series = pd.Series([customer.frequency] + rfm["frequency"].tolist())
    m_series = pd.Series([customer.monetary] + rfm["monetary"].tolist())

    r_score = int(pd.qcut(r_series.rank(method="first"), q=5, labels=[5, 4, 3, 2, 1])[0])
    f_score = int(pd.qcut(f_series.rank(method="first"), q=5, labels=[1, 2, 3, 4, 5])[0])
    m_score = int(pd.qcut(m_series.rank(method="first"), q=5, labels=[1, 2, 3, 4, 5])[0])
    rfm_score = r_score + f_score + m_score

    if rfm_score >= 13:
        segment = "\U0001f3c6 Champion"
        action  = "VIP treatment, early access, loyalty rewards"
    elif rfm_score >= 10:
        segment = "\U0001f49a Loyal"
        action  = "Upsell & cross-sell, referral program"
    elif rfm_score >= 7:
        segment = "\U0001f331 Potential"
        action  = "Nurture with personalized offers, free shipping threshold"
    elif rfm_score >= 4:
        segment = "\u26a0\ufe0f At Risk"
        action  = "Win-back campaign, discount voucher, personal outreach"
    else:
        segment = "\u274c Lost"
        action  = "Last-chance promotion or deprioritize marketing spend"

    return SegmentResponse(
        segment=segment,
        rfm_score=float(rfm_score),
        r_score=r_score, f_score=f_score, m_score=m_score,
        action=action,
    )


@router.post("/clv", response_model=CLVResponse)
def predict_customer_lifetime_value(customer: CustomerRFM, customer_id: int = 0):
    """
    Predict Customer Lifetime Value using the BG/NBD + Gamma-Gamma model stack.
    Returns predicted purchases, expected revenue per purchase, and total CLV
    over a 30-day horizon.
    """
    try:
        bgf, ggf = _model_cache.get_clv_models()
        if bgf is None or ggf is None:
            raise FileNotFoundError(
                "CLV models are not available. Please run the training pipeline first."
            )

        t = 30  # 30-day prediction horizon
        purchases = float(bgf.predict(t, customer.frequency, customer.recency, customer.recency + 10))
        aov = ggf.conditional_expected_average_profit(customer.frequency, customer.monetary)

        clv_val = float(ggf.customer_lifetime_value(
            bgf,
            pd.Series([customer.frequency]),
            pd.Series([customer.recency]),
            pd.Series([customer.recency + 10]),
            pd.Series([customer.monetary]),
            time=1,
            discount_rate=0.01,
        ).iloc[0])

        return CLVResponse(
            customer_id=customer_id,
            predicted_purchases=round(purchases, 2),
            expected_revenue=round(float(aov), 2),
            clv=round(float(clv_val), 2),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
def get_product_recommendations(customer_id: int, limit: int = 5):
    """
    Return product recommendations for a customer using the Implicit ALS model.
    Falls back to empty recommendations when the model is not trained or unavailable.
    Product metadata is enriched from the dim_products table when the DB is reachable.
    """
    try:
        from src.back_end.ml.recommendation import get_recommendations
        recs = get_recommendations(customer_id, N=limit, model_dir=os.path.join(PROJECT_ROOT, "models"))
    except Exception as e:
        print(f"[API Warning] Implicit ALS model not trained or error: {e}")
        recs = []

    products_enriched = []
    if recs:
        try:
            engine = get_engine()
            id_list = ",".join(str(x) for x in recs)
            with engine.connect() as conn:
                res = conn.execute(text(
                    f"SELECT product_id, name, category FROM dim_products WHERE product_id IN ({id_list})"
                ))
                for r in res:
                    products_enriched.append({
                        "product_id": int(r[0]),
                        "name":       str(r[1] or "Unknown Product"),
                        "category":   str(r[2] or "Unknown Category"),
                    })
        except Exception as e:
            print(f"[API Warning] Database offline during recommendation enrichment: {e}")
            for r_id in recs:
                products_enriched.append({
                    "product_id": int(r_id),
                    "name":       f"Product #{r_id}",
                    "category":   "Unknown Category",
                })

    return {
        "customer_id":               customer_id,
        "recommended_product_ids":   recs,
        "products":                  products_enriched,
        "generated_at":              datetime.utcnow().isoformat(),
    }
