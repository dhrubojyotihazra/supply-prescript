"""
SupplyPrescript - Week 3 & 4 Automated Test Suite
Tests Circuit Breaker logic, Stream Routing to DLQ Iceberg Table [1.1.1],
Time Travel Queries, Snapshot Rollback, and REST API Endpoints.
"""

import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.circuit_breaker import CircuitBreakerManager, CircuitState
from engine.iceberg_engine import IcebergTableManager
from fastapi.testclient import TestClient
from api.main import app

def test_circuit_breaker_threshold():
    cb = CircuitBreakerManager(threshold_error_rate=2.0)
    assert cb.state == CircuitState.CLOSED
    assert cb.get_error_rate() == 0.5

    # Simulate error spike (4.5% error rate)
    res = cb.simulate_anomaly_spike(4.5)
    assert res["is_tripped"] is True
    assert res["state"] == "OPEN"
    assert res["active_destination"] == "warehouses_dlq_stream"

    # Reset circuit breaker
    reset_res = cb.reset_circuit()
    assert reset_res["is_tripped"] is False
    assert reset_res["state"] == "CLOSED"
    assert reset_res["active_destination"] == "warehouses_main_stream"
    print("[PASS] test_circuit_breaker_threshold passed successfully!")

def test_iceberg_time_travel_and_rollback():
    mgr = IcebergTableManager()
    snaps = mgr.get_snapshots()
    assert len(snaps) >= 3

    # Time travel query for pre-anomaly snapshot
    tt_res = mgr.time_travel_query("snap-1002")
    assert tt_res["status"] == "success"
    assert tt_res["snapshot_id"] == "snap-1002"
    assert tt_res["is_pre_anomaly"] is True
    assert len(tt_res["data_sample"]) > 0

    # Execute snapshot rollback
    rb_res = mgr.rollback_to_snapshot("snap-1002")
    assert rb_res["status"] == "success"
    assert rb_res["restored_snapshot_id"] == "snap-1002"
    print("[PASS] test_iceberg_time_travel_and_rollback passed successfully!")

def test_api_remediation_endpoints():
    client = TestClient(app)

    # 1. GET /remediation/status
    res1 = client.get("/remediation/status")
    assert res1.status_code == 200
    assert res1.json()["status"] == "success"

    # 2. POST /remediation/simulate-stream (Trip circuit breaker)
    res2 = client.post("/remediation/simulate-stream", json={"error_rate_percent": 4.8})
    assert res2.status_code == 200
    assert res2.json()["simulation"]["is_tripped"] is True

    # 3. GET /remediation/incidents
    res3 = client.get("/remediation/incidents")
    assert res3.status_code == 200
    assert len(res3.json()) > 0

    # 4. POST /iceberg/time-travel
    res4 = client.post("/iceberg/time-travel", json={"snapshot_id": "snap-1002"})
    assert res4.status_code == 200
    assert res4.json()["snapshot_id"] == "snap-1002"

    # 5. POST /iceberg/rollback
    res5 = client.post("/iceberg/rollback", json={"snapshot_id": "snap-1002"})
    assert res5.status_code == 200
    assert res5.json()["status"] == "success"

    # 6. POST /remediation/reset
    res6 = client.post("/remediation/reset")
    assert res6.status_code == 200
    assert res6.json()["status"] == "success"
    print("[PASS] test_api_remediation_endpoints passed successfully!")

if __name__ == "__main__":
    print("Running SupplyPrescript Week 3 & 4 Automated Test Suite...")
    test_circuit_breaker_threshold()
    test_iceberg_time_travel_and_rollback()
    test_api_remediation_endpoints()
    print("ALL REMEDIATION & TIME TRAVEL TESTS PASSED 100%!")
