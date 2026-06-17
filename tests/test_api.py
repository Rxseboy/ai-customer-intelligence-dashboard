"""
tests/test_api.py
==================
FastAPI endpoint integration tests (no real DB needed — uses TestClient).
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from fastapi.testclient import TestClient
from src.back_end.api.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    print(f"GET / => {r.status_code} | {data['message'][:50]}")


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "model_ready" in data
    assert "mlflow_ready" in data
    print(f"GET /health => {r.status_code} | mlflow_ready={data['mlflow_ready']}")


def test_predict_churn_valid():
    payload = {"recency": 120, "frequency": 2, "monetary": 150.0}
    r = client.post("/predict/churn", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert 0.0 <= data["churn_probability"] <= 1.0
    assert data["risk_level"] in ["\U0001f534 High", "\U0001f7e1 Medium", "\U0001f7e2 Low"]
    risk_safe = data["risk_level"].encode("ascii", errors="replace").decode()
    print(f"POST /predict/churn => {r.status_code} | risk={risk_safe} prob={data['churn_probability']:.3f}")


def test_predict_churn_negative_monetary():
    """Pydantic contract harus reject monetary <= 0."""
    r = client.post("/predict/churn", json={"recency": 30, "frequency": 2, "monetary": -100})
    assert r.status_code == 422
    print(f"POST /predict/churn (negative monetary) => {r.status_code} (422 expected OK)")


def test_predict_churn_zero_monetary():
    r = client.post("/predict/churn", json={"recency": 30, "frequency": 2, "monetary": 0})
    assert r.status_code == 422
    print(f"POST /predict/churn (zero monetary) => {r.status_code} (422 expected OK)")


def test_predict_churn_low_recency():
    """Customer dengan recency rendah (baru beli) seharusnya low risk."""
    r = client.post("/predict/churn", json={"recency": 5, "frequency": 10, "monetary": 2000.0})
    assert r.status_code == 200
    data = r.json()
    risk_safe = data["risk_level"].encode("ascii", errors="replace").decode()
    print(f"POST /predict/churn (active customer) => risk={risk_safe}")


def test_monitoring_drift_status():
    r = client.get("/monitoring/drift")
    assert r.status_code == 200
    data = r.json()
    assert "retrain_signal_active" in data
    assert "baseline_exists" in data
    assert "checked_at" in data
    print(f"GET /monitoring/drift => {r.status_code} | signal={data['retrain_signal_active']}")


def test_insights_ask_empty_question():
    """Pertanyaan kosong harus ditolak Pydantic (min_length=5)."""
    r = client.post("/insights/ask", json={"question": "Hi"})
    assert r.status_code == 422
    print(f"POST /insights/ask (too short) => {r.status_code} (422 expected OK)")


def test_insights_ask_injection():
    """SQL injection dalam pertanyaan harus diblokir."""
    r = client.post("/insights/ask", json={"question": "DROP TABLE orders --"})
    assert r.status_code == 422
    print(f"POST /insights/ask (injection) => {r.status_code} (422 expected OK)")


if __name__ == "__main__":
    tests = [
        test_root,
        test_health,
        test_predict_churn_valid,
        test_predict_churn_negative_monetary,
        test_predict_churn_zero_monetary,
        test_predict_churn_low_recency,
        test_monitoring_drift_status,
        test_insights_ask_empty_question,
        test_insights_ask_injection,
    ]

    passed = failed = 0
    print("\n--- FastAPI Endpoint Tests ---")
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL - {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"  API RESULTS: {passed} passed / {failed} failed")
    print(f"{'='*50}")
    if failed > 0:
        sys.exit(1)
