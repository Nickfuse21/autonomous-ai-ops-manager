from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_trace_id
from app.schemas.contracts import (
    BusinessEvent,
    DecisionCycleRequest,
    DecisionCycleResponse,
    ForecastPredictRequest,
    ForecastPredictResponse,
)
from app.services.engine import DecisionCycleEngine

router = APIRouter(prefix="/api", tags=["ops-manager"])
engine = DecisionCycleEngine()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "autonomous-ai-ops-manager",
        "version": "0.1.0",
        "capabilities": ["decision_cycle", "forecast", "approvals", "audit_export"],
    }


@router.post("/forecast/predict", response_model=ForecastPredictResponse)
def predict_sales_forecast(payload: ForecastPredictRequest) -> ForecastPredictResponse:
    result = engine.predict_sales(payload.recent_sales, payload.traffic, payload.conversions)
    return ForecastPredictResponse(
        predicted_sales=result.predicted_sales,
        confidence=result.confidence,
        version=result.version,
    )


@router.get("/dashboard")
def dashboard(
    limit: int = Query(default=20, ge=0, le=500),
    decision_status: str | None = Query(default=None),
) -> dict:
    """Single round-trip bootstrap for the ops dashboard."""
    audit = engine.audit_log
    total_count = len(audit)
    decision_items = list(audit)
    if decision_status:
        decision_items = [r for r in decision_items if r.get("decision_status") == decision_status]
    if limit:
        decision_items = decision_items[-limit:]
    pending = engine.list_pending_approvals()
    return {
        "impact": engine.get_impact_summary(),
        "pending_approvals": {"count": len(pending), "items": pending},
        "decisions": {
            "items": decision_items,
            "total_count": total_count,
            "count": len(decision_items),
        },
        "server_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@router.post("/cycle/run", response_model=DecisionCycleResponse)
def run_cycle(payload: DecisionCycleRequest) -> DecisionCycleResponse:
    if not payload.events:
        raise HTTPException(status_code=400, detail="events cannot be empty")
    trace_id = get_trace_id()
    return engine.run_cycle(trace_id=trace_id, events=payload.events, autonomous_mode=payload.autonomous_mode)


@router.get("/decisions")
def list_decisions(
    limit: int = Query(default=0, ge=0, le=500),
    decision_status: str | None = Query(default=None),
) -> dict:
    items = engine.audit_log
    if decision_status:
        items = [record for record in items if record.get("decision_status") == decision_status]
    if limit:
        items = items[-limit:]
    return {"count": len(items), "total_count": len(engine.audit_log), "items": items}


@router.post("/cycle/demo", response_model=DecisionCycleResponse)
def run_demo_cycle(autonomous_mode: bool = Query(default=True)) -> DecisionCycleResponse:
    data_file = Path(__file__).resolve().parents[3] / "data" / "simulated" / "business_events.csv"
    if not data_file.exists():
        raise HTTPException(status_code=404, detail=f"Demo data file not found: {data_file}")

    events: List[BusinessEvent] = []
    with data_file.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            events.append(
                BusinessEvent(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    product_id=row["product_id"],
                    sales=float(row["sales"]),
                    traffic=float(row["traffic"]),
                    conversions=float(row["conversions"]),
                    cost=float(row["cost"]),
                    inventory=float(row["inventory"]),
                    price=float(row["price"]),
                )
            )

    trace_id = get_trace_id()
    return engine.run_cycle(trace_id=trace_id, events=events, autonomous_mode=autonomous_mode)


@router.get("/approvals")
def list_pending_approvals() -> dict:
    items = engine.list_pending_approvals()
    return {"count": len(items), "items": items}


@router.post("/approvals/{decision_id}/approve")
def approve_pending_decision(decision_id: str) -> dict:
    try:
        return engine.approve_decision(decision_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/approvals/{decision_id}/reject")
def reject_pending_decision(decision_id: str) -> dict:
    try:
        return engine.reject_decision(decision_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/impact-summary")
def impact_summary() -> dict:
    return engine.get_impact_summary()
