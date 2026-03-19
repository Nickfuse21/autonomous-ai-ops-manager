from __future__ import annotations

from typing import List

from app.schemas.contracts import BusinessEvent, IssueType, SituationReport


class SituationAwarenessAgent:
    def run(self, events: List[BusinessEvent]) -> SituationReport:
        if len(events) < 3:
            return SituationReport(
                issue_type=IssueType.NORMAL,
                confidence=0.4,
                observations=["Not enough events to infer a reliable business state."],
                risk_score=0.2,
            )

        recent = events[-3:]
        baseline = events[:-3] or events

        avg_recent_sales = sum(e.sales for e in recent) / len(recent)
        avg_base_sales = sum(e.sales for e in baseline) / len(baseline)
        avg_recent_traffic = sum(e.traffic for e in recent) / len(recent)
        avg_recent_conv_rate = sum((e.conversions / max(e.traffic, 1.0)) for e in recent) / len(recent)
        avg_base_conv_rate = sum((e.conversions / max(e.traffic, 1.0)) for e in baseline) / len(baseline)

        sales_drop_pct = 1.0 - (avg_recent_sales / max(avg_base_sales, 1.0))
        conversion_drop_pct = 1.0 - (avg_recent_conv_rate / max(avg_base_conv_rate, 0.0001))
        observations = [
            f"Recent sales change: {round(-sales_drop_pct * 100, 2)}%.",
            f"Recent conversion change: {round(-conversion_drop_pct * 100, 2)}%.",
            f"Recent average traffic: {round(avg_recent_traffic, 2)}.",
        ]

        issue_type = IssueType.NORMAL
        risk_score = 0.1
        confidence = 0.6

        if sales_drop_pct > 0.2 and conversion_drop_pct > 0.15:
            issue_type = IssueType.CONVERSION_DROP
            risk_score = min(1.0, 0.5 + sales_drop_pct + conversion_drop_pct / 2)
            confidence = 0.82
            observations.append("Sales dropped while traffic remains present; likely conversion friction.")
        elif sales_drop_pct > 0.2:
            issue_type = IssueType.SALES_DROP
            risk_score = min(1.0, 0.45 + sales_drop_pct)
            confidence = 0.77
            observations.append("Sustained sales drop detected.")

        if sum(e.inventory for e in recent) / len(recent) < 30:
            issue_type = IssueType.INVENTORY_RISK
            risk_score = max(risk_score, 0.72)
            confidence = max(confidence, 0.75)
            observations.append("Inventory is moving near risk threshold.")

        return SituationReport(
            issue_type=issue_type,
            confidence=confidence,
            observations=observations,
            risk_score=risk_score,
            context={
                "sales_drop_pct": round(sales_drop_pct, 4),
                "conversion_drop_pct": round(conversion_drop_pct, 4),
                "recent_avg_traffic": round(avg_recent_traffic, 2),
            },
        )
