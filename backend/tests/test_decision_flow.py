from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def build_event(idx: int, sales: float, traffic: float, conversions: float):
    return {
        "timestamp": (datetime(2026, 3, 1) + timedelta(days=idx)).isoformat(),
        "product_id": "SKU-001",
        "sales": sales,
        "traffic": traffic,
        "conversions": conversions,
        "cost": 400,
        "inventory": 220 - idx * 3,
        "price": 99,
    }


def test_closed_loop_sales_drop_executes_action():
    events = [
        build_event(0, 120, 1000, 62),
        build_event(1, 121, 1010, 63),
        build_event(2, 118, 995, 60),
        build_event(3, 116, 990, 58),
        build_event(4, 90, 1020, 36),
        build_event(5, 86, 1030, 34),
        build_event(6, 82, 1040, 33),
    ]
    response = client.post("/api/cycle/run", json={"events": events, "autonomous_mode": True})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["chosen_action"]["action_type"] in {
        "reduce_price",
        "run_discount_campaign",
        "hold",
    }
    assert body["execution"] is not None
    assert "trace_id" in body
    assert body["outcome"] is not None


def test_empty_events_rejected():
    response = client.post("/api/cycle/run", json={"events": [], "autonomous_mode": True})
    assert response.status_code == 400


def test_demo_cycle_and_audit_endpoint():
    response = client.post("/api/cycle/demo")
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["trace_id"] == body["trace_id"]

    audit = client.get("/api/decisions")
    assert audit.status_code == 200
    assert audit.json()["count"] >= 1
    assert "timestamp" in audit.json()["items"][-1]


def test_human_approval_flow():
    queued = client.post("/api/cycle/demo?autonomous_mode=false")
    assert queued.status_code == 200
    queued_body = queued.json()
    assert queued_body["decision"]["status"] == "needs_human_approval"
    assert queued_body["execution"] is None

    pending = client.get("/api/approvals")
    assert pending.status_code == 200
    assert pending.json()["count"] >= 1
    decision_id = pending.json()["items"][0]["decision_id"]

    approved = client.post(f"/api/approvals/{decision_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] in {"executed", "failed"}


def test_human_reject_flow():
    queued = client.post("/api/cycle/demo?autonomous_mode=false")
    assert queued.status_code == 200

    pending = client.get("/api/approvals")
    assert pending.status_code == 200
    assert pending.json()["count"] >= 1
    decision_id = pending.json()["items"][0]["decision_id"]

    rejected = client.post(f"/api/approvals/{decision_id}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected_by_policy"


def test_impact_summary_endpoint():
    summary = client.get("/api/impact-summary")
    assert summary.status_code == 200
    body = summary.json()
    for key in {
        "total_decisions",
        "executed_count",
        "pending_approval_count",
        "avg_decision_score",
        "positive_outcome_rate",
        "estimated_revenue_lift_score",
    }:
        assert key in body
