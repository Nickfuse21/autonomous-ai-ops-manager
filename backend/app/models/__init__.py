"""Pluggable model interfaces (forecasting, etc.)."""

from app.models.forecast import ForecastResult, SalesForecaster

__all__ = ["ForecastResult", "SalesForecaster"]
