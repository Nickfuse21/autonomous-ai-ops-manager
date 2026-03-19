from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from app.schemas.contracts import ActionType, CandidateAction, SituationReport


@dataclass(frozen=True)
class PolicyConfig:
    max_discount_pct: float = 0.2
    max_campaign_budget: float = 5000.0
    min_inventory_after_sale: float = 20.0
    confidence_threshold: float = 0.6
    autonomous_threshold: float = 0.68


class PolicyEngine:
    def __init__(self, config: PolicyConfig | None = None) -> None:
        self.config = config or PolicyConfig()

    def evaluate_action(self, report: SituationReport, action: CandidateAction) -> Tuple[bool, List[str], float]:
        checks: List[str] = []
        passed = True
        rule_score = 1.0

        if report.confidence < self.config.confidence_threshold:
            passed = False
            checks.append("Situation confidence below minimum threshold.")
            rule_score -= 0.5

        if action.action_type == ActionType.REDUCE_PRICE:
            discount = float(action.params.get("discount_pct", 0.0))
            if discount <= 0 or discount > self.config.max_discount_pct:
                passed = False
                checks.append("Discount violates policy cap.")
                rule_score -= 0.4

        if action.action_type == ActionType.RUN_DISCOUNT_CAMPAIGN:
            budget = float(action.params.get("budget", 0.0))
            if budget <= 0 or budget > self.config.max_campaign_budget:
                passed = False
                checks.append("Campaign budget violates policy cap.")
                rule_score -= 0.4

        if action.action_type == ActionType.RESTOCK:
            quantity = float(action.params.get("quantity", 0.0))
            if quantity <= 0:
                passed = False
                checks.append("Restock quantity must be positive.")
                rule_score -= 0.4

        if action.action_type == ActionType.HOLD:
            checks.append("No-op hold action selected.")

        return passed, checks, max(0.0, min(1.0, rule_score))
