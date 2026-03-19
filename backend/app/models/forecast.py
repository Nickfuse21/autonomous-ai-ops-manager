from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass
class ForecastResult:
    predicted_sales: float
    confidence: float
    version: str = "heuristic-0.1"


class SalesForecaster:
    """
    Lightweight forecaster with a clean interface.
    You can swap this with XGBoost/LSTM later without changing agent code.
    """

    def predict_next_sales(self, recent_sales: List[float], traffic: float, conversions: float) -> ForecastResult:
        if not recent_sales:
            return ForecastResult(predicted_sales=0.0, confidence=0.2)

        arr = np.array(recent_sales[-7:], dtype=float)
        trend = float(np.mean(arr))
        conv_rate = (conversions / max(traffic, 1.0)) if traffic > 0 else 0.0

        uplift_factor = 0.85 + min(conv_rate * 5, 0.3)
        predicted = max(0.0, trend * uplift_factor)
        confidence = 0.55 + min(len(arr) / 20.0, 0.35)

        return ForecastResult(predicted_sales=predicted, confidence=min(confidence, 0.9))
