from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.agents.action_agent import ActionAgent
from app.agents.awareness_agent import SituationAwarenessAgent
from app.agents.decision_agent import DecisionAgent
from app.agents.ingestion_agent import IngestionAgent
from app.agents.outcome_agent import OutcomeEvaluatorAgent
from app.core.logging import get_logger
from app.memory.vector_store import DecisionMemoryStore
from app.models.forecast import ForecastResult, SalesForecaster
from app.policy.rules import PolicyEngine
from app.schemas.contracts import BusinessEvent, DecisionCycleResponse
from app.schemas.contracts import DecisionStatus
from app.storage.local_store import LocalAuditStore


class DecisionCycleEngine:
    def __init__(self) -> None:
        self.ingestion_agent = IngestionAgent()
        self.awareness_agent = SituationAwarenessAgent()
        self.policy_engine = PolicyEngine()
        self.forecaster = SalesForecaster()
        self.decision_agent = DecisionAgent(self.policy_engine, self.forecaster)
        self.action_agent = ActionAgent()
        self.outcome_agent = OutcomeEvaluatorAgent()
        self.memory_store = DecisionMemoryStore()
        self.audit_store = LocalAuditStore()
        self.audit_log: list[dict] = self.audit_store.read_all()
        self.pending_approvals: dict[str, dict[str, Any]] = {}

    def predict_sales(self, recent_sales: List[float], traffic: float, conversions: float) -> ForecastResult:
        """Expose the forecaster for direct API / tooling without running a full decision cycle."""
        return self.forecaster.predict_next_sales(recent_sales, traffic, conversions)

    def _persist_audit(self, record: dict[str, Any]) -> None:
        self.audit_log.append(record)
        self.audit_store.append(record)

    def _build_audit_record(
        self,
        trace_id: str,
        decision,
        outcome_effectiveness: str | None = None,
        outcome_score: float | None = None,
    ) -> dict[str, Any]:
        return {
            "trace_id": trace_id,
            "decision_id": decision.decision_id,
            "timestamp": decision.timestamp.isoformat(),
            "decision_status": decision.status.value,
            "chosen_action": decision.chosen_action.action_type.value,
            "decision_score": decision.chosen_action.total_score,
            "outcome_effectiveness": outcome_effectiveness,
            "outcome_score": outcome_score,
            "policy_checks": decision.policy_checks,
            "model_versions": decision.model_versions,
        }

    def run_cycle(self, trace_id: str, events: List[BusinessEvent], autonomous_mode: bool = True) -> DecisionCycleResponse:
        logger = get_logger(trace_id)
        ingestion = self.ingestion_agent.run(events)
        logger.info("Ingestion complete with %s events", len(ingestion.cleaned_events))

        situation = self.awareness_agent.run(ingestion.cleaned_events)
        logger.info("Situation detected: %s", situation.issue_type.value)

        memory_query = " | ".join(situation.observations)
        memory_matches = self.memory_store.search(memory_query)
        decision = self.decision_agent.decide(trace_id, situation, ingestion.cleaned_events, memory_matches, autonomous_mode)
        logger.info("Decision made: %s score=%s", decision.chosen_action.action_type.value, decision.chosen_action.total_score)

        execution = None
        outcome = None

        if decision.status == DecisionStatus.NEEDS_HUMAN_APPROVAL:
            self.pending_approvals[decision.decision_id] = {
                "decision": decision,
                "events": ingestion.cleaned_events,
                "memory_query": memory_query,
            }
            self._persist_audit(self._build_audit_record(trace_id=trace_id, decision=decision))
            logger.info("Decision queued for human approval: %s", decision.decision_id)
        else:
            execution = self.action_agent.execute(decision)
            if execution.success:
                decision.status = DecisionStatus.EXECUTED
                logger.info("Action executed successfully: %s", execution.action_type.value)
            else:
                logger.warning("Action execution failed/skipped: %s", execution.error)

            outcome = self.outcome_agent.evaluate(decision, execution, ingestion.cleaned_events)
            logger.info("Outcome effectiveness: %s score=%s", outcome.effectiveness, outcome.score)

            self.memory_store.add(
                context_text=memory_query,
                payload={
                    "decision_id": decision.decision_id,
                    "action": decision.chosen_action.action_type.value,
                    "score": decision.chosen_action.total_score,
                    "outcome_effectiveness": outcome.effectiveness,
                    "outcome_score": outcome.score,
                },
            )

            self._persist_audit(
                self._build_audit_record(
                    trace_id=trace_id,
                    decision=decision,
                    outcome_effectiveness=outcome.effectiveness,
                    outcome_score=outcome.score,
                )
            )

        return DecisionCycleResponse(
            trace_id=trace_id,
            ingestion=ingestion,
            situation=situation,
            decision=decision,
            execution=execution,
            outcome=outcome,
            memory_matches=memory_matches,
        )

    def list_pending_approvals(self) -> List[dict[str, Any]]:
        items: List[dict[str, Any]] = []
        for decision_id, data in self.pending_approvals.items():
            decision = data["decision"]
            items.append(
                {
                    "decision_id": decision_id,
                    "trace_id": decision.trace_id,
                    "issue_type": decision.report.issue_type.value,
                    "chosen_action": decision.chosen_action.action_type.value,
                    "decision_score": decision.chosen_action.total_score,
                    "created_at": decision.timestamp.isoformat(),
                }
            )
        return items

    def approve_decision(self, decision_id: str) -> dict[str, Any]:
        pending = self.pending_approvals.get(decision_id)
        if not pending:
            raise KeyError("Pending decision not found.")

        decision = pending["decision"]
        events = pending["events"]
        memory_query = pending["memory_query"]
        decision.status = DecisionStatus.APPROVED

        execution = self.action_agent.execute(decision)
        if execution.success:
            decision.status = DecisionStatus.EXECUTED
        else:
            decision.status = DecisionStatus.FAILED

        outcome = self.outcome_agent.evaluate(decision, execution, events)
        self.memory_store.add(
            context_text=memory_query,
            payload={
                "decision_id": decision.decision_id,
                "action": decision.chosen_action.action_type.value,
                "score": decision.chosen_action.total_score,
                "outcome_effectiveness": outcome.effectiveness,
                "outcome_score": outcome.score,
            },
        )
        self._persist_audit(
            self._build_audit_record(
                trace_id=decision.trace_id,
                decision=decision,
                outcome_effectiveness=outcome.effectiveness,
                outcome_score=outcome.score,
            )
        )
        self.pending_approvals.pop(decision_id, None)

        return {
            "decision_id": decision_id,
            "status": decision.status.value,
            "execution_success": execution.success,
            "outcome_effectiveness": outcome.effectiveness,
            "outcome_score": outcome.score,
        }

    def reject_decision(self, decision_id: str) -> dict[str, Any]:
        pending = self.pending_approvals.get(decision_id)
        if not pending:
            raise KeyError("Pending decision not found.")

        decision = pending["decision"]
        decision.status = DecisionStatus.REJECTED_BY_POLICY
        self._persist_audit(self._build_audit_record(trace_id=decision.trace_id, decision=decision))
        self.pending_approvals.pop(decision_id, None)
        return {"decision_id": decision_id, "status": decision.status.value}

    def get_impact_summary(self) -> dict[str, Any]:
        records = self.audit_log
        if not records:
            return {
                "total_decisions": 0,
                "executed_count": 0,
                "pending_approval_count": len(self.pending_approvals),
                "avg_decision_score": 0.0,
                "positive_outcome_rate": 0.0,
                "estimated_revenue_lift_score": 0.0,
            }

        executed = [r for r in records if r.get("decision_status") == DecisionStatus.EXECUTED.value]
        positive = [r for r in executed if r.get("outcome_effectiveness") == "positive"]
        scores = [float(r.get("decision_score", 0.0)) for r in records if r.get("decision_score") is not None]
        outcome_scores = [float(r.get("outcome_score", 0.0)) for r in executed if r.get("outcome_score") is not None]

        return {
            "total_decisions": len(records),
            "executed_count": len(executed),
            "pending_approval_count": len(self.pending_approvals),
            "avg_decision_score": round(sum(scores) / max(len(scores), 1), 4),
            "positive_outcome_rate": round(len(positive) / max(len(executed), 1), 4),
            "estimated_revenue_lift_score": round(sum(outcome_scores), 4),
        }
