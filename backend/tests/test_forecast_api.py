from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_includes_version_and_capabilities():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert "forecast" in body["capabilities"]


def test_forecast_predict_empty_sales():
    r = client.post(
        "/api/forecast/predict",
        json={"recent_sales": [], "traffic": 100.0, "conversions": 5.0},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["predicted_sales"] == 0.0
    assert data["confidence"] == 0.2
    assert "version" in data


def test_forecast_predict_with_history():
    r = client.post(
        "/api/forecast/predict",
        json={
            "recent_sales": [120.0, 130.0, 125.0, 140.0, 135.0, 128.0, 132.0],
            "traffic": 1000.0,
            "conversions": 120.0,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["predicted_sales"] > 0
    assert 0.0 < data["confidence"] <= 0.9


def test_request_id_header_echoed():
    r = client.get("/api/health", headers={"X-Request-ID": "custom-trace-abc"})
    assert r.status_code == 200
    assert r.headers.get("x-request-id") == "custom-trace-abc"
