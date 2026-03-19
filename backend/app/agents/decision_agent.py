from __future__ import annotations

from datetime import datetime
from typing import List

from app.models.forecast import SalesForecaster
from app.policy.rules import PolicyEngine
from app.schemas.contracts import (
    ActionType,
    BusinessEvent,
    CandidateAction,
    DecisionRecord,
    DecisionStatus,
    SituationReport,
)


class DecisionAgent:
    def __init__(self, policy_engine: PolicyEngine, forecaster: SalesForecaster) -> None:
        self.policy_engine = policy_engine
        self.forecaster = forecaster
        self.model_versions = {"forecast_model": "heuristic-0.1", "llm_policy": "template-reasoner-0.1"}

    def _reasoning_score(self, report: SituationReport, action: CandidateAction) -> tuple[float, str]:
        # Simple reasoning layer for local machine usage.
        # You can later replace this with a real LLM call.
        if report.issue_type.value in {"sales_drop", "conversion_drop"} and action.action_type in {
            ActionType.REDUCE_PRICE,
            ActionType.RUN_DISCOUNT_CAMPAIGN,
        }:
            return 0.8, "Business pressure detected, incentive action is reasonable."
        if report.issue_type.value == "inventory_risk" and action.action_type == ActionType.RESTOCK:
            return 0.82, "Inventory risk detected, restocking reduces stockout chance."
        if action.action_type == ActionType.HOLD:
            return 0.45, "Uncertainty is high, hold can avoid wrong action."
        return 0.55, "Action is possible but evidence is moderate."

    def _build_candidates(self, report: SituationReport) -> List[CandidateAction]:
        if report.issue_type.value in {"sales_drop", "conversion_drop"}:
            return [
                CandidateAction(
                    action_type=ActionType.REDUCE_PRICE,
                    params={"discount_pct": 0.1},
                    rationale="Reduce price to recover conversion quickly.",
                ),
                CandidateAction(
                    action_type=ActionType.RUN_DISCOUNT_CAMPAIGN,
                    params={"budget": 1500.0, "channel": "email"},
                    rationale="Run targeted campaign to reactivate intent-heavy traffic.",
                ),
                CandidateAction(action_type=ActionType.HOLD, params={}, rationale="Wait for more signal before intervention."),
            ]
        if report.issue_type.value == "inventory_risk":
            return [
                CandidateAction(
                    action_type=ActionType.RESTOCK,
                    params={"quantity": 200},
                    rationale="Restock proactively to avoid stockout losses.",
                ),
                CandidateAction(action_type=ActionType.SEND_ALERT, params={"severity": "high"}, rationale="Notify operations team."),
            ]
        return [CandidateAction(action_type=ActionType.HOLD, params={}, rationale="System is stable.")]

    def decide(
        self,
        trace_id: str,
        report: SituationReport,
        events: List[BusinessEvent],
        memory_matches: List[dict],
        autonomous_mode: bool,
    ) -> DecisionRecord:
        candidates = self._build_candidates(report)
        recent_sales = [e.sales for e in events][-10:]
        latest = events[-1] if events else BusinessEvent(
            timestamp=datetime.utcnow(),
            product_id="na",
            sales=0,
            traffic=0,
            conversions=0,
            cost=0,
            inventory=0,
            price=1,
        )
        forecast = self.forecaster.predict_next_sales(recent_sales, latest.traffic, latest.conversions)

        policy_notes = []
        for candidate in candidates:
            allowed, checks, rule_score = self.policy_engine.evaluate_action(report, candidate)
            llm_score, llm_reason = self._reasoning_score(report, candidate)
            predicted_uplift = max(0.0, (forecast.predicted_sales - latest.sales) / max(latest.sales, 1.0))
            ml_score = min(1.0, max(0.0, predicted_uplift + forecast.confidence / 3))
            memory_bonus = 0.05 if memory_matches else 0.0

            candidate.rule_score = rule_score if allowed else max(0.0, rule_score - 0.2)
            candidate.ml_score = ml_score
            candidate.llm_score = llm_score
            candidate.expected_uplift = round(predicted_uplift, 4)
            # Beginner-friendly scoring formula:
            # 1) Rules are most important.
            # 2) Forecast and reasoning are secondary signals.
            candidate.total_score = round(
                min(1.0, 0.4 * candidate.rule_score + 0.35 * candidate.ml_score + 0.25 * candidate.llm_score + memory_bonus),
                4,
            )
            candidate.rationale = f"{candidate.rationale} {llm_reason}"
            policy_notes.extend(checks)

        candidates.sort(key=lambda c: c.total_score, reverse=True)
        chosen = candidates[0]
        status = DecisionStatus.APPROVED

        if chosen.total_score < self.policy_engine.config.autonomous_threshold:
            status = DecisionStatus.NEEDS_HUMAN_APPROVAL
            policy_notes.append("Top action score below autonomous threshold.")

        if not autonomous_mode and status == DecisionStatus.APPROVED:
            status = DecisionStatus.NEEDS_HUMAN_APPROVAL
            policy_notes.append("Autonomous mode is disabled.")

        return DecisionRecord(
            trace_id=trace_id,
            report=report,
            options=candidates,
            chosen_action=chosen,
            status=status,
            policy_checks=policy_notes,
            model_versions=self.model_versions,
        )
