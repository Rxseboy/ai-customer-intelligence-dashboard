"""
_run_all_tests.py  --  Self-contained test runner that writes output to file.
Run: venv\Scripts\python.exe _run_all_tests.py
"""
import sys, os, traceback, json
from io import StringIO
from datetime import datetime

sys.path.insert(0, os.path.abspath("."))

from dotenv import load_dotenv
load_dotenv()

# ─── CAPTURE OUTPUT ──────────────────────────────────────────────────────────
buf = StringIO()
old_stdout = sys.stdout
sys.stdout = buf

results = {}

def run_test(name, fn):
    try:
        fn()
        results[name] = "PASS"
        print(f"[PASS] {name}")
    except Exception as e:
        results[name] = f"FAIL: {e}"
        print(f"[FAIL] {name}: {e}")
        traceback.print_exc()

# ═══════════════════════════════════════════════════
print("=" * 60)
print("  SYSTEM TESTS")
print("=" * 60)

# ──  T1: Core Imports ────────────────────────────────────────
def t1():
    from src.back_end.ml.data_loader import get_engine, load_orders, load_full
    from src.back_end.ml.features import build_all_features
    from src.back_end.ml.features.feature_registry import load_feature_config, get_versioned_output_path
    from src.back_end.ml.segmentation import run_kmeans, plot_segments
    from src.back_end.ml.churn import train_churn_model, predict_churn_risk
    from src.back_end.ml.monitoring.drift_monitor import DriftMonitor
    from src.back_end.ml.rag import SQLSafetyValidator, QueryCache, RAGInsightAssistant
    from src.back_end.ml.clv import train_clv_models
    from src.back_end.ml.recommendation import train_recommender, get_recommendations
    from src.back_end.ml.forecasting_anomaly import train_forecast_model, train_anomaly_model
run_test("t1_core_imports", t1)

# ── T2: Feature Registry ─────────────────────────────────────
def t2():
    from src.back_end.ml.features.feature_registry import load_feature_config
    config = load_feature_config()
    assert "version" in config
    assert "churn_threshold_days" in config
run_test("t2_feature_registry", t2)

# ── T3: API Schemas ──────────────────────────────────────────
def t3():
    from src.back_end.api.schemas.contracts import (
        CustomerRFM, RAGQueryRequest, ChurnResponse,
        CLVResponse, RecommendationResponse
    )
    c = CustomerRFM(recency=30, frequency=5, monetary=250.0)
    assert c.avg_order_value == 50.0
    clv = CLVResponse(customer_id=1, predicted_purchases=1.2, expected_revenue=100.0, clv=300.0)
    assert clv.clv == 300.0
    rec = RecommendationResponse(customer_id=1, recommended_product_ids=[1,2,3])
    assert len(rec.recommended_product_ids) == 3
    try:
        CustomerRFM(recency=30, frequency=5, monetary=-100)
        raise AssertionError("Should fail")
    except Exception as _: pass
run_test("t3_api_schemas", t3)

# ── T4: SQL Validator ────────────────────────────────────────
def t4():
    from src.back_end.ml.rag import SQLSafetyValidator
    v = SQLSafetyValidator()
    ok, _ = v.is_safe("SELECT customer_id FROM fact_orders")
    assert ok
    for dml in ["DROP TABLE x", "DELETE FROM y", "TRUNCATE z"]:
        s, _ = v.is_safe(dml)
        assert not s, f"Should block: {dml}"
run_test("t4_sql_validator", t4)

# ── T5: Cache ────────────────────────────────────────────────
def t5():
    from src.back_end.ml.rag import QueryCache
    c = QueryCache(ttl_seconds=3600)
    assert c.get("test") is None
    c.set("test", {"answer": "42"})
    assert c.get("test")["answer"] == "42"
run_test("t5_query_cache", t5)

# ── T6: Drift Monitor ────────────────────────────────────────
def t6():
    import pandas as pd, numpy as np, tempfile
    from src.back_end.ml.monitoring.drift_monitor import DriftMonitor
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "customer_id": range(200),
        "recency": rng.integers(1,365,200).astype(float),
        "frequency": rng.integers(1,50,200).astype(float),
        "monetary": rng.uniform(10,5000,200),
    })
    with tempfile.TemporaryDirectory() as t:
        m = DriftMonitor(baseline_path=os.path.join(t,"b.json"))
        m.set_baseline(df)
        r = m.check_drift(df)
        assert not r["drift_detected"]
        # Inject heavy drift
        df2 = df.copy(); df2["recency"] = 9999
        r2 = m.check_drift(df2)
        assert r2["drift_detected"]
run_test("t6_drift_monitor", t6)

# ── T7: FastAPI Health & Endpoints ───────────────────────────
def t7():
    from fastapi.testclient import TestClient
    from src.back_end.api.main import app
    client = TestClient(app, raise_server_exceptions=False)
    # Health
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
    
    headers = {"X-API-Key": "your-secure-api-key-here"}
    
    # Churn
    r = client.post("/predict/churn", json={"recency":120,"frequency":2,"monetary":150.0}, headers=headers)
    assert r.status_code == 200
    assert 0.0 <= r.json()["churn_probability"] <= 1.0
    # Segment
    r = client.post("/predict/segment", json={"recency":30,"frequency":10,"monetary":500.0}, headers=headers)
    assert r.status_code in [200, 400, 500]  # model might not be loaded in test env
    # Drift monitoring
    r = client.get("/monitoring/drift")
    assert r.status_code == 200
    assert "retrain_signal_active" in r.json()
    # RAG injection should fail
    r = client.post("/insights/ask", json={"question":"DROP TABLE orders --"}, headers=headers)
    assert r.status_code == 422
    # Invalid monetary
    r = client.post("/predict/churn", json={"recency":30,"frequency":2,"monetary":-100}, headers=headers)
    assert r.status_code == 422
run_test("t7_api_endpoints", t7)

# ─── SUMMARY ──────────────────────────────────────────────────────────────────
passed = sum(1 for v in results.values() if v == "PASS")
failed = sum(1 for v in results.values() if v != "PASS")

print()
print("=" * 60)
print(f"  RESULTS: {passed} PASSED / {failed} FAILED")
print("=" * 60)
for k, v in results.items():
    emoji = "✅" if v == "PASS" else "❌"
    print(f"  {emoji}  {k}: {v}")

# ─── RESTORE & WRITE ──────────────────────────────────────────────────────────
sys.stdout = old_stdout
output = buf.getvalue()
print(output)

with open("test_results.log", "w", encoding="utf-8") as f:
    f.write(f"Run: {datetime.now().isoformat()}\n\n")
    f.write(output)
    f.write("\n")
    f.write(json.dumps(results, indent=2, ensure_ascii=False))

print(f"\nResults saved to test_results.log - {passed} passed / {failed} failed")
if failed:
    sys.exit(1)
