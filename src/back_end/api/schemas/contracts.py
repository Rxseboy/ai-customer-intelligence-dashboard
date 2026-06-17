"""
src/back_end/api/schemas/contracts.py
=======================================
Centralized Pydantic Contracts — Customer Intelligence System API

Semua request/response schema didefinisikan di sini untuk:
  - Validasi ketat di API front-gate sebelum menyentuh model
  - Dokumentasi otomatis OpenAPI/Swagger
  - Mencegah bad input silently masuk ke ML pipeline

Rules:
  - monetary HARUS positif
  - recency HARUS >= 0
  - query RAG tidak boleh kosong atau terlalu panjang
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


# ── INPUT SCHEMAS ─────────────────────────────────────────────────────────────

class CustomerRFM(BaseModel):
    """Input data untuk prediksi churn dan segmentasi."""

    recency: float = Field(
        ...,
        ge=0,
        description="Hari sejak terakhir beli. Harus >= 0.",
        examples=[45],
    )
    frequency: float = Field(
        ...,
        ge=1,
        description="Jumlah total order. Harus >= 1.",
        examples=[3],
    )
    monetary: float = Field(
        ...,
        gt=0,
        description="Total spend dalam USD. Harus > 0.",
        examples=[250.0],
    )
    avg_order_value: Optional[float] = Field(
        None,
        gt=0,
        description="Rata-rata nilai order. Opsional — dihitung otomatis jika tidak disediakan.",
        examples=[83.3],
    )

    @field_validator("monetary", "recency", "frequency")
    @classmethod
    def must_be_finite(cls, v: float) -> float:
        import math
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Nilai tidak boleh NaN atau Inf.")
        return round(v, 6)

    @model_validator(mode="after")
    def compute_aov_if_missing(self) -> "CustomerRFM":
        if self.avg_order_value is None:
            self.avg_order_value = round(self.monetary / max(self.frequency, 1), 4)
        return self


class RAGQueryRequest(BaseModel):
    """Input untuk endpoint AI Insight Assistant."""

    question: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Pertanyaan bisnis dalam bahasa natural (max 500 karakter).",
        examples=["Siapa 5 customer dengan revenue tertinggi bulan ini?"],
    )
    language: Optional[str] = Field(
        "id",
        description="Bahasa respons: 'id' (Indonesia) atau 'en' (English).",
        examples=["id"],
    )
    d_from: Optional[str] = Field(None, description="Start date filter")
    d_to: Optional[str] = Field(None, description="End date filter")
    granularity: Optional[str] = Field(None, description="Time granularity filter")
    segments: Optional[list[str]] = Field(None, description="List of chosen segment IDs")

    @field_validator("question")
    @classmethod
    def no_sql_injection(cls, v: str) -> str:
        """Basic sanity check — RAG juga punya SQL Validator, ini layer pertama."""
        blocked = [";<", "/*", "*/", "--", "xp_", "EXEC("]
        for token in blocked:
            if token.lower() in v.lower():
                raise ValueError(f"Karakter tidak diizinkan dalam pertanyaan: '{token}'")
        return v.strip()


# ── RESPONSE SCHEMAS ──────────────────────────────────────────────────────────

class ChurnResponse(BaseModel):
    """Response prediksi churn untuk satu customer."""
    churn_probability: float = Field(..., ge=0, le=1)
    risk_level:        str
    prediction:        str
    recency_days:      float
    message:           str


class SegmentResponse(BaseModel):
    """Response segmentasi RFM untuk satu customer."""
    segment:   str
    rfm_score: float
    r_score:   int
    f_score:   int
    m_score:   int
    action:    str


class InsightResponse(BaseModel):
    """Response summary bisnis dari seluruh customer base."""
    total_customers:    int
    total_revenue:      float
    avg_monetary:       float
    avg_recency_days:   float
    churn_rate_pct:     float
    pareto_top20_pct:   float
    generated_at:       str


class RAGQueryResponse(BaseModel):
    """Response dari AI Insight Assistant."""
    answer:       str
    sql:          Optional[str] = None
    cached:       bool = False
    error:        Optional[str] = None
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HealthResponse(BaseModel):
    """Response health check."""
    status:        str
    model_ready:   bool
    data_ready:    bool
    mlflow_ready:  bool
    timestamp:     str
    cache_stats:   Optional[dict] = None


class DriftStatusResponse(BaseModel):
    """Response status drift monitoring."""
    retrain_signal_active: bool
    last_drift_log:        Optional[dict] = None
    baseline_exists:       bool
    checked_at:            str


class CLVResponse(BaseModel):
    """Response prediksi Customer Lifetime Value (CLV)."""
    customer_id:         int
    predicted_purchases: float
    expected_revenue:    float
    clv:                 float
    generated_at:        str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class RecommendationResponse(BaseModel):
    """Response rekomendasi produk."""
    customer_id:         int
    recommended_product_ids: list[int]
    generated_at:        str = Field(default_factory=lambda: datetime.utcnow().isoformat())

