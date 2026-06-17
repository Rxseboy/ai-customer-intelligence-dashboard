"""
tests/test_system.py
=====================
System integration tests - run tanpa DB connection.
Verifikasi semua core module imports, contracts, validators, feature registry.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()


def test_1_core_imports():
    print("\n--- Test 1: Core Imports ---")
    from src.back_end.ml.data_loader import get_engine, load_orders, load_full
    from src.back_end.ml.features import build_all_features
    from src.back_end.ml.features.feature_registry import load_feature_config, get_versioned_output_path
    from src.back_end.ml.segmentation import run_kmeans, plot_segments
    from src.back_end.ml.churn import train_churn_model, predict_churn_risk
    from src.back_end.ml.monitoring.drift_monitor import DriftMonitor
    from src.front_end.insights import generate_insights
    print("OK - semua import berhasil")


def test_2_feature_registry():
    print("\n--- Test 2: Feature Registry ---")
    from src.back_end.ml.features.feature_registry import load_feature_config, bump_version
    config = load_feature_config()
    assert "version" in config
    assert "churn_threshold_days" in config
    print(f"OK - version={config['version']}, churn_threshold={config['churn_threshold_days']}")


def test_3_api_schemas():
    print("\n--- Test 3: API Schemas (Pydantic) ---")
    from src.back_end.api.schemas.contracts import CustomerRFM, RAGQueryRequest, ChurnResponse
    # Valid input
    c = CustomerRFM(recency=30, frequency=5, monetary=250.0)
    assert c.avg_order_value == 50.0
    print(f"OK - CustomerRFM avg_order_value={c.avg_order_value}")

    # Invalid: negative monetary
    try:
        CustomerRFM(recency=30, frequency=5, monetary=-100)
        assert False, "Should reject negative monetary"
    except Exception:
        print("OK - negative monetary rejected")

    # Invalid: SQL injection in RAG question
    try:
        RAGQueryRequest(question="DROP TABLE orders --")
        assert False, "Should reject SQL injection"
    except Exception:
        print("OK - SQL injection in question rejected")


def test_4_sql_validator():
    print("\n--- Test 4: SQL Safety Validator ---")
    from src.back_end.ml.rag import SQLSafetyValidator
    v = SQLSafetyValidator()

    safe, _ = v.is_safe("SELECT customer_id, SUM(sale_price) FROM fact_orders GROUP BY 1")
    assert safe, "Valid SELECT should pass"
    print("OK - valid SELECT passed")

    for dangerous in ["DROP TABLE orders", "DELETE FROM users",
                      "TRUNCATE fact_orders", "INSERT INTO x VALUES (1)",
                      "UPDATE users SET email='x'"]:
        ok, reason = v.is_safe(dangerous)
        assert not ok, f"Should have blocked: {dangerous}"
    print("OK - semua DML blocked")


def test_5_query_cache():
    print("\n--- Test 5: Query Cache ---")
    from src.back_end.ml.rag import QueryCache
    cache = QueryCache(ttl_seconds=3600)

    assert cache.get("test question") is None
    cache.set("test question", {"answer": "42", "sql": "SELECT 1"})
    result = cache.get("test question")
    assert result is not None
    assert result["answer"] == "42"

    # Case-insensitive
    cache.set("Revenue?", {"answer": "999"})
    assert cache.get("revenue?") is not None

    stats = cache.stats()
    assert stats["cache_size"] == 2
    print(f"OK - cache hits={stats['hits']}, misses={stats['misses']}, size={stats['cache_size']}")


def test_6_feature_versioning(tmp_path_str=None):
    print("\n--- Test 6: Feature Store Versioning ---")
    import tempfile, json
    from src.back_end.ml.features.feature_registry import get_versioned_output_path

    with tempfile.TemporaryDirectory() as tmpdir:
        path = get_versioned_output_path(tmpdir, version="v99")
        assert "features_v99" in path
        meta_path = os.path.join(path, "metadata.json")
        assert os.path.exists(meta_path)
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["version"] == "v99"
    print("OK - versioned output folder created with metadata.json")


def test_7_drift_monitor_stats():
    print("\n--- Test 7: DriftMonitor Stats Computation ---")
    import pandas as pd
    import numpy as np
    from src.back_end.ml.monitoring.drift_monitor import DriftMonitor
    import tempfile

    # Create synthetic RFM
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "customer_id": range(200),
        "recency":     rng.integers(1, 365, 200).astype(float),
        "frequency":   rng.integers(1, 50, 200).astype(float),
        "monetary":    rng.uniform(10, 5000, 200),
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        baseline_path = os.path.join(tmpdir, "baseline.json")
        monitor = DriftMonitor(baseline_path=baseline_path, threshold_std=3.0)
        monitor.set_baseline(df)

        # No drift on same data
        report = monitor.check_drift(df)
        assert not report["drift_detected"]
        print("OK - no drift on same data")

        # Simulate drift
        df_noisy = df.copy()
        df_noisy["recency"] = df_noisy["recency"] * 10
        df_noisy["monetary"] = df_noisy["monetary"] / 100

        report2 = monitor.check_drift(df_noisy)
        assert report2["drift_detected"]
        print(f"OK - drift detected in: {report2['drifted_features']}")


def test_8_api_schema_responses():
    print("\n--- Test 8: Response Schema Validation ---")
    from src.back_end.api.schemas.contracts import (
        ChurnResponse, SegmentResponse, InsightResponse,
        HealthResponse, DriftStatusResponse
    )
    from datetime import datetime

    cr = ChurnResponse(
        churn_probability=0.75,
        risk_level="High",
        prediction="CHURN",
        recency_days=120.0,
        message="At risk"
    )
    assert 0 <= cr.churn_probability <= 1
    print(f"OK - ChurnResponse valid: prob={cr.churn_probability}")

    hr = HealthResponse(
        status="healthy",
        model_ready=True,
        data_ready=True,
        mlflow_ready=False,
        timestamp=datetime.utcnow().isoformat()
    )
    assert hr.status == "healthy"
    print("OK - HealthResponse valid")


if __name__ == "__main__":
    tests = [
        test_1_core_imports,
        test_2_feature_registry,
        test_3_api_schemas,
        test_4_sql_validator,
        test_5_query_cache,
        test_6_feature_versioning,
        test_7_drift_monitor_stats,
        test_8_api_schema_responses,
    ]

    passed = 0
    failed = 0
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
    print(f"  RESULTS: {passed} passed / {failed} failed")
    print(f"{'='*50}")
    if failed > 0:
        sys.exit(1)
