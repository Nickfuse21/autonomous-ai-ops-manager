from __future__ import annotations

from typing import Dict, List

from app.schemas.contracts import ActionExecutionResult, BusinessEvent, DecisionRecord, OutcomeReport


class OutcomeEvaluatorAgent:
    def evaluate(
        self,
        decision: DecisionRecord,
        execution: ActionExecutionResult | None,
        events: List[BusinessEvent],
    ) -> OutcomeReport:
        recent = events[-3:] if len(events) >= 3 else events
        baseline = events[:-3] if len(events) > 3 else events

        def avg(items: List[BusinessEvent], field: str) -> float:
            if not items:
                return 0.0
            return sum(getattr(x, field) for x in items) / len(items)

        pre = {
            "sales": round(avg(baseline, "sales"), 3),
            "traffic": round(avg(baseline, "traffic"), 3),
            "conversions": round(avg(baseline, "conversions"), 3),
        }
        post = {
            "sales": round(avg(recent, "sales"), 3),
            "traffic": round(avg(recent, "traffic"), 3),
            "conversions": round(avg(recent, "conversions"), 3),
        }
        deltas: Dict[str, float] = {
            key: round(post[key] - pre[key], 3) for key in pre
        }
        sales_gain = (post["sales"] - pre["sales"]) / max(pre["sales"], 1.0)
        score = max(-1.0, min(1.0, sales_gain))

        effectiveness = "neutral"
        notes = []
        if execution and not execution.success:
            effectiveness = "failed_execution"
            notes.append("Action execution failed or was skipped.")
            score = min(score, 0.0)
        elif score > 0.05:
            effectiveness = "positive"
            notes.append("Post-action sales metrics improved.")
        elif score < -0.05:
            effectiveness = "negative"
            notes.append("Post-action sales metrics declined.")
        else:
            notes.append("Outcome inconclusive in current attribution window.")

        return OutcomeReport(
            decision_id=decision.decision_id,
            trace_id=decision.trace_id,
            pre_kpis=pre,
            post_kpis=post,
            deltas=deltas,
            effectiveness=effectiveness,
            score=round(score, 4),
            notes=notes,
        )
