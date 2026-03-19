from __future__ import annotations

import time
from typing import Dict

from app.schemas.contracts import ActionExecutionResult, ActionType, DecisionRecord, DecisionStatus


class ActionAgent:
    def __init__(self) -> None:
        self._idempotent_store: Dict[str, ActionExecutionResult] = {}
        self.dead_letter_queue: list[dict] = []

    def _execute_mock(self, decision: DecisionRecord) -> dict:
        action = decision.chosen_action
        if action.action_type == ActionType.REDUCE_PRICE:
            return {"price_change": -action.params.get("discount_pct", 0.0), "target": "catalog-service"}
        if action.action_type == ActionType.RUN_DISCOUNT_CAMPAIGN:
            return {"campaign_id": f"cmp-{decision.decision_id[:8]}", "channel": action.params.get("channel", "email")}
        if action.action_type == ActionType.RESTOCK:
            return {"restock_qty": action.params.get("quantity", 0), "target": "inventory-planner"}
        if action.action_type == ActionType.SEND_ALERT:
            return {"alert_sent": True, "severity": action.params.get("severity", "medium")}
        return {"noop": True}

    def execute(self, decision: DecisionRecord, max_retries: int = 2) -> ActionExecutionResult:
        idempotency_key = f"{decision.trace_id}:{decision.chosen_action.action_type.value}"
        if idempotency_key in self._idempotent_store:
            return self._idempotent_store[idempotency_key]

        if decision.status in {DecisionStatus.NEEDS_HUMAN_APPROVAL, DecisionStatus.REJECTED_BY_POLICY}:
            result = ActionExecutionResult(
                decision_id=decision.decision_id,
                trace_id=decision.trace_id,
                action_type=decision.chosen_action.action_type,
                success=False,
                idempotency_key=idempotency_key,
                details={"skipped": True},
                error="Action skipped due to decision status.",
            )
            self._idempotent_store[idempotency_key] = result
            return result

        retries = 0
        while retries <= max_retries:
            try:
                payload = self._execute_mock(decision)
                result = ActionExecutionResult(
                    decision_id=decision.decision_id,
                    trace_id=decision.trace_id,
                    action_type=decision.chosen_action.action_type,
                    success=True,
                    idempotency_key=idempotency_key,
                    retries=retries,
                    details=payload,
                )
                self._idempotent_store[idempotency_key] = result
                return result
            except Exception as exc:  # pragma: no cover
                retries += 1
                if retries > max_retries:
                    failed = ActionExecutionResult(
                        decision_id=decision.decision_id,
                        trace_id=decision.trace_id,
                        action_type=decision.chosen_action.action_type,
                        success=False,
                        idempotency_key=idempotency_key,
                        retries=retries,
                        error=str(exc),
                    )
                    self.dead_letter_queue.append({"decision_id": decision.decision_id, "error": str(exc)})
                    self._idempotent_store[idempotency_key] = failed
                    return failed
                time.sleep(0.1 * retries)

        unreachable = ActionExecutionResult(
            decision_id=decision.decision_id,
            trace_id=decision.trace_id,
            action_type=decision.chosen_action.action_type,
            success=False,
            idempotency_key=idempotency_key,
            retries=max_retries,
            error="Unknown execution state.",
        )
        self.dead_letter_queue.append({"decision_id": decision.decision_id, "error": "Unknown state"})
        self._idempotent_store[idempotency_key] = unreachable
        return unreachable
