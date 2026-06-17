"""
tests/test_contracts.py
========================
Unit tests for Pydantic API contracts (src/back_end/api/schemas/contracts.py)
These tests run in CI/CD without requiring a database connection.
"""

import pytest
import math
from pydantic import ValidationError

from src.back_end.api.schemas.contracts import (
    CustomerRFM,
    RAGQueryRequest,
    ChurnResponse,
    SegmentResponse,
    InsightResponse,
    RAGQueryResponse,
)


class TestCustomerRFM:
    """CustomerRFM input validation tests."""

    def test_valid_input(self):
        c = CustomerRFM(recency=30, frequency=5, monetary=250.0)
        assert c.recency == 30
        assert c.frequency == 5
        assert c.monetary == 250.0

    def test_auto_avg_order_value(self):
        """avg_order_value should be computed automatically if not provided."""
        c = CustomerRFM(recency=10, frequency=4, monetary=200.0)
        assert c.avg_order_value == 50.0

    def test_explicit_avg_order_value(self):
        c = CustomerRFM(recency=10, frequency=4, monetary=200.0, avg_order_value=75.0)
        assert c.avg_order_value == 75.0

    def test_negative_monetary_rejected(self):
        with pytest.raises(ValidationError):
            CustomerRFM(recency=30, frequency=5, monetary=-100.0)

    def test_zero_monetary_rejected(self):
        with pytest.raises(ValidationError):
            CustomerRFM(recency=30, frequency=5, monetary=0.0)

    def test_negative_recency_rejected(self):
        with pytest.raises(ValidationError):
            CustomerRFM(recency=-1, frequency=5, monetary=100.0)

    def test_nan_monetary_rejected(self):
        with pytest.raises(ValidationError):
            CustomerRFM(recency=30, frequency=5, monetary=float("nan"))

    def test_inf_monetary_rejected(self):
        with pytest.raises(ValidationError):
            CustomerRFM(recency=30, frequency=5, monetary=float("inf"))

    def test_zero_frequency_rejected(self):
        with pytest.raises(ValidationError):
            CustomerRFM(recency=30, frequency=0, monetary=100.0)


class TestRAGQueryRequest:
    """RAGQueryRequest input validation tests."""

    def test_valid_question(self):
        r = RAGQueryRequest(question="Berapa total revenue bulan ini?")
        assert r.question == "Berapa total revenue bulan ini?"

    def test_question_stripped(self):
        r = RAGQueryRequest(question="  Siapa top customer?  ")
        assert not r.question.startswith(" ")

    def test_too_short_question_rejected(self):
        with pytest.raises(ValidationError):
            RAGQueryRequest(question="Hi")

    def test_too_long_question_rejected(self):
        with pytest.raises(ValidationError):
            RAGQueryRequest(question="x" * 501)

    def test_sql_injection_blocked_semicolon(self):
        with pytest.raises(ValidationError):
            RAGQueryRequest(question="Show users;< DROP TABLE orders")

    def test_sql_comment_blocked(self):
        with pytest.raises(ValidationError):
            RAGQueryRequest(question="Show me users -- DROP TABLE")

    def test_default_language(self):
        r = RAGQueryRequest(question="What is total revenue?")
        assert r.language == "id"

    def test_custom_language(self):
        r = RAGQueryRequest(question="What is total revenue?", language="en")
        assert r.language == "en"


class TestRAGSQLValidator:
    """SQLSafetyValidator unit tests — independent from the full chain."""

    def setup_method(self):
        from src.back_end.ml.rag import SQLSafetyValidator
        self.validator = SQLSafetyValidator()

    def test_safe_select(self):
        ok, _ = self.validator.is_safe(
            "SELECT customer_id, SUM(sale_price) FROM fact_orders GROUP BY 1"
        )
        assert ok

    @pytest.mark.parametrize("dangerous_sql", [
        "DROP TABLE orders",
        "DELETE FROM users",
        "TRUNCATE fact_orders",
        "INSERT INTO users VALUES (1, 'hacked')",
        "UPDATE users SET email = 'x'",
        "ALTER TABLE users ADD COLUMN x TEXT",
        "GRANT ALL ON orders TO hacker",
    ])
    def test_dangerous_sql_blocked(self, dangerous_sql):
        safe, reason = self.validator.is_safe(dangerous_sql)
        assert not safe, f"Should have blocked: {dangerous_sql}"
        assert reason != "OK"

    def test_no_select_rejected(self):
        safe, reason = self.validator.is_safe("EXEC xp_cmdshell('whoami')")
        assert not safe

    def test_too_long_sql_rejected(self):
        safe, reason = self.validator.is_safe("SELECT " + "x" * 2100)
        assert not safe


class TestFeatureRegistry:
    """Feature Store registry versioning tests."""

    def test_load_default_config(self, tmp_path, monkeypatch):
        """Should return default config dict if no JSON found."""
        import json
        from src.back_end.ml.features import feature_registry

        # Redirect config path to tmp_path
        config_path = tmp_path / "feature_config.json"
        monkeypatch.setattr(feature_registry, "CONFIG_PATH", config_path)

        config = feature_registry.load_feature_config()
        assert "churn_threshold_days" in config
        assert "version" in config
        assert config_path.exists()

    def test_bump_version(self, tmp_path, monkeypatch):
        """Version should increment correctly."""
        from src.back_end.ml.features import feature_registry

        config_path = tmp_path / "feature_config.json"
        monkeypatch.setattr(feature_registry, "CONFIG_PATH", config_path)

        config = {"version": "v1", "churn_threshold_days": 90}
        bumped = feature_registry.bump_version(config)
        assert bumped["version"] == "v2"

    def test_versioned_output_path(self, tmp_path):
        """Versioned output path should be created and contain metadata.json."""
        import json
        from src.back_end.ml.features.feature_registry import get_versioned_output_path

        path = get_versioned_output_path(str(tmp_path), version="v99")
        assert "features_v99" in path
        assert (tmp_path / "features_v99" / "metadata.json").exists()


class TestQueryCache:
    """QueryCache in-memory caching tests."""

    def test_cache_miss_then_hit(self):
        from src.back_end.ml.rag import QueryCache

        cache = QueryCache(ttl_seconds=3600)
        question = "What is the total revenue?"
        result = {"answer": "500000", "sql": "SELECT SUM(sale_price) FROM fact_orders"}

        assert cache.get(question) is None       # miss
        cache.set(question, result)
        cached = cache.get(question)
        assert cached is not None                # hit
        assert cached["answer"] == "500000"

    def test_cache_key_case_insensitive(self):
        from src.back_end.ml.rag import QueryCache

        cache = QueryCache(ttl_seconds=3600)
        cache.set("Total Revenue?", {"answer": "999"})
        assert cache.get("total revenue?") is not None

    def test_cache_stats(self):
        from src.back_end.ml.rag import QueryCache

        cache = QueryCache(ttl_seconds=3600)
        cache.get("q1")               # miss
        cache.set("q1", {"answer": "x"})
        cache.get("q1")               # hit
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["cache_size"] == 1
