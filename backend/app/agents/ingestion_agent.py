from __future__ import annotations

from statistics import mean, pstdev
from typing import List

from app.schemas.contracts import BusinessEvent, IngestionResult


class IngestionAgent:
    def run(self, events: List[BusinessEvent]) -> IngestionResult:
        cleaned = [e for e in events if e.sales >= 0 and e.traffic >= 0 and e.price > 0]
        anomalies: List[str] = []

        if cleaned:
            sales_values = [e.sales for e in cleaned]
            avg_sales = mean(sales_values)
            sigma = pstdev(sales_values) if len(sales_values) > 1 else 0.0
            for event in cleaned:
                if sigma > 0 and abs(event.sales - avg_sales) > 2 * sigma:
                    anomalies.append(
                        f"Outlier sales detected for {event.product_id} at {event.timestamp.isoformat()}."
                    )

            summary = {
                "avg_sales": round(avg_sales, 2),
                "avg_traffic": round(mean([e.traffic for e in cleaned]), 2),
                "avg_conversion_rate": round(
                    mean([e.conversions / max(e.traffic, 1.0) for e in cleaned]), 4
                ),
                "avg_inventory": round(mean([e.inventory for e in cleaned]), 2),
            }
        else:
            summary = {"avg_sales": 0.0, "avg_traffic": 0.0, "avg_conversion_rate": 0.0, "avg_inventory": 0.0}

        return IngestionResult(cleaned_events=cleaned, anomalies=anomalies, summary=summary)
