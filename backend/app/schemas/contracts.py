from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class IssueType(str, Enum):
    SALES_DROP = "sales_drop"
    CONVERSION_DROP = "conversion_drop"
    INVENTORY_RISK = "inventory_risk"
    TRAFFIC_SPIKE = "traffic_spike"
    NORMAL = "normal"


class ActionType(str, Enum):
    REDUCE_PRICE = "reduce_price"
    RUN_DISCOUNT_CAMPAIGN = "run_discount_campaign"
    RESTOCK = "restock"
    SEND_ALERT = "send_alert"
    HOLD = "hold"


class DecisionStatus(str, Enum):
    APPROVED = "approved"
    REJECTED_BY_POLICY = "rejected_by_policy"
    NEEDS_HUMAN_APPROVAL = "needs_human_approval"
    EXECUTED = "executed"
    FAILED = "failed"


class BusinessEvent(BaseModel):
    timestamp: datetime
    product_id: str
    sales: float = Field(ge=0)
    traffic: float = Field(ge=0)
    conversions: float = Field(ge=0)
    cost: float = Field(ge=0)
    inventory: float = Field(ge=0)
    price: float = Field(gt=0)


class IngestionResult(BaseModel):
    cleaned_events: List[BusinessEvent]
    anomalies: List[str]
    summary: Dict[str, float]


class SituationReport(BaseModel):
    issue_type: IssueType
    confidence: float = Field(ge=0, le=1)
    observations: List[str]
    risk_score: float = Field(ge=0, le=1)
    context: Dict[str, Any] = Field(default_factory=dict)


class CandidateAction(BaseModel):
    action_type: ActionType
    params: Dict[str, Any] = Field(default_factory=dict)
    expected_uplift: float = 0.0
    rule_score: float = Field(default=0.0, ge=0, le=1)
    ml_score: float = Field(default=0.0, ge=0, le=1)
    llm_score: float = Field(default=0.0, ge=0, le=1)
    total_score: float = Field(default=0.0, ge=0, le=1)
    rationale: str = ""


class DecisionRecord(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    report: SituationReport
    options: List[CandidateAction]
    chosen_action: CandidateAction
    status: DecisionStatus
    policy_checks: List[str] = Field(default_factory=list)
    model_versions: Dict[str, str] = Field(default_factory=dict)


class ActionExecutionResult(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str
    trace_id: str
    action_type: ActionType
    success: bool
    idempotency_key: str
    retries: int = 0
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class OutcomeReport(BaseModel):
    decision_id: str
    trace_id: str
    pre_kpis: Dict[str, float]
    post_kpis: Dict[str, float]
    deltas: Dict[str, float]
    effectiveness: str
    score: float = Field(ge=-1, le=1)
    notes: List[str] = Field(default_factory=list)


class DecisionCycleRequest(BaseModel):
    events: List[BusinessEvent]
    autonomous_mode: bool = True


class DecisionCycleResponse(BaseModel):
    trace_id: str
    ingestion: IngestionResult
    situation: SituationReport
    decision: DecisionRecord
    execution: Optional[ActionExecutionResult]
    outcome: Optional[OutcomeReport]
    memory_matches: List[Dict[str, Any]] = Field(default_factory=list)
