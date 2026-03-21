from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dashboard_bootstrap_endpoint():
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert "server_time" in body
    assert "impact" in body
    assert "pending_approvals" in body
    assert "decisions" in body

    impact = body["impact"]
    for key in (
        "total_decisions",
        "executed_count",
        "pending_approval_count",
        "avg_decision_score",
        "positive_outcome_rate",
        "estimated_revenue_lift_score",
    ):
        assert key in impact

    pa = body["pending_approvals"]
    assert "count" in pa
    assert "items" in pa

    dec = body["decisions"]
    assert "items" in dec
    assert "total_count" in dec
    assert "count" in dec


def test_dashboard_respects_limit_and_status():
    client.post("/api/cycle/demo")
    limited = client.get("/api/dashboard?limit=1")
    assert limited.status_code == 200
    assert limited.json()["decisions"]["count"] <= 1
