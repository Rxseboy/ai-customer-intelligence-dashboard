import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from src.back_end.api.schemas.contracts import DriftStatusResponse
from src.back_end.api.dependencies import get_api_key
from src.back_end.api.services.model_cache import ModelCache, DRIFT_LOG_PATH, RETRAIN_FLAG, BASELINE_PATH

router = APIRouter(prefix="/monitoring/drift", tags=["Monitoring"])
_model_cache = ModelCache()

@router.get("", response_model=DriftStatusResponse)
def get_drift_status():
    retrain_active = os.path.exists(RETRAIN_FLAG)
    baseline_exists = os.path.exists(BASELINE_PATH)

    last_log = None
    if os.path.exists(DRIFT_LOG_PATH):
        try:
            with open(DRIFT_LOG_PATH, "r") as f:
                logs = json.load(f)
            last_log = logs[-1] if logs else None
        except Exception:
            pass

    return DriftStatusResponse(
        retrain_signal_active=retrain_active,
        last_drift_log=last_log,
        baseline_exists=baseline_exists,
        checked_at=datetime.utcnow().isoformat(),
    )

@router.post("/check", dependencies=[Depends(get_api_key)])
def run_drift_check():
    try:
        from src.back_end.ml.monitoring.drift_monitor import DriftMonitor
        rfm = _model_cache.get_rfm()
        monitor = DriftMonitor()
        report = monitor.check_drift(rfm)
        if report["drift_detected"]:
            monitor.trigger_retrain_signal(report)
        return {
            "success": True,
            "drift_detected": report["drift_detected"],
            "drifted_features": report["drifted_features"],
            "retrain_triggered": report["drift_detected"],
            "checked_at": report["checked_at"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drift check failed: {e}")
