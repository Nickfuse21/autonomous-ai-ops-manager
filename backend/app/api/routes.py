from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_trace_id
from app.schemas.contracts import BusinessEvent, DecisionCycleRequest, DecisionCycleResponse
from app.services.engine import DecisionCycleEngine

router = APIRouter(prefix="/api", tags=["ops-manager"])
engine = DecisionCycleEngine()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "autonomous-ai-ops-manager"}


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
