"""
Forecasting Module for Cash Flow Intelligence

Time series forecasting and cash flow projection capabilities.
"""

from .cash_flow_forecaster import (
    CashFlowForecaster,
    ForecastResult,
    ForecastScenario
)
from .trend_analyzer import (
    TrendAnalyzer,
    TrendResult,
    SeasonalPattern
)

__all__ = [
    'CashFlowForecaster',
    'ForecastResult',
    'ForecastScenario',
    'TrendAnalyzer',
    'TrendResult',
    'SeasonalPattern',
]
