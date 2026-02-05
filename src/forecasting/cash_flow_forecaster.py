"""
Cash Flow Forecaster

Time series forecasting for SMB cash flow using Prophet and statistical methods.
Provides cash position projections, runway calculations, and scenario analysis.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import numpy as np

# Try to import Prophet, fallback to simple methods if not available
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

logger = logging.getLogger(__name__)


class ForecastScenario(Enum):
    """Forecast scenario types"""
    BASELINE = "baseline"           # Status quo projection
    OPTIMISTIC = "optimistic"       # +20% revenue, -10% expenses
    PESSIMISTIC = "pessimistic"     # -20% revenue, +10% expenses
    GROWTH = "growth"               # Revenue growth acceleration
    COST_CUTTING = "cost_cutting"   # Expense reduction scenario


@dataclass
class ForecastResult:
    """Result of cash flow forecast"""
    forecast_dates: List[datetime]
    predicted_cash: List[float]
    lower_bound: List[float]
    upper_bound: List[float]
    confidence_level: float
    runway_months: float
    zero_cash_date: Optional[datetime]
    scenario: ForecastScenario
    model_type: str
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forecast_dates": [d.isoformat() for d in self.forecast_dates],
            "predicted_cash": self.predicted_cash,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "confidence_level": self.confidence_level,
            "runway_months": self.runway_months,
            "zero_cash_date": self.zero_cash_date.isoformat() if self.zero_cash_date else None,
            "scenario": self.scenario.value,
            "model_type": self.model_type,
            "metrics": self.metrics
        }


@dataclass
class CashFlowData:
    """Input data for forecasting"""
    dates: List[datetime]
    cash_inflows: List[float]      # Revenue, collections, etc.
    cash_outflows: List[float]     # Expenses, payroll, etc.
    cash_balances: List[float]     # Ending cash balance

    @property
    def net_cash_flow(self) -> List[float]:
        """Calculate net cash flow"""
        return [i - o for i, o in zip(self.cash_inflows, self.cash_outflows)]

    def to_dataframe_format(self) -> List[Dict]:
        """Convert to format suitable for Prophet"""
        return [
            {"ds": d, "y": b}
            for d, b in zip(self.dates, self.cash_balances)
        ]


class CashFlowForecaster:
    """
    Cash flow forecasting engine for SMBs.

    Provides:
    - Time series forecasting using Prophet (if available) or statistical methods
    - Multiple scenario analysis
    - Runway calculation
    - Cash crunch early warning

    Example:
    ```python
    forecaster = CashFlowForecaster()

    data = CashFlowData(
        dates=[datetime(2024, 1, 1), datetime(2024, 2, 1), ...],
        cash_inflows=[100000, 95000, ...],
        cash_outflows=[80000, 85000, ...],
        cash_balances=[50000, 60000, ...]
    )

    result = forecaster.forecast(data, periods=6)
    print(f"Cash runway: {result.runway_months} months")
    ```
    """

    def __init__(
        self,
        confidence_level: float = 0.80,
        use_prophet: bool = True
    ):
        """
        Initialize forecaster.

        Args:
            confidence_level: Confidence interval (0.80 = 80%)
            use_prophet: Whether to use Prophet (if available)
        """
        self.confidence_level = confidence_level
        self.use_prophet = use_prophet and PROPHET_AVAILABLE

        if self.use_prophet:
            logger.info("Using Prophet for forecasting")
        else:
            logger.info("Using statistical methods for forecasting (Prophet not available)")

    def forecast(
        self,
        data: CashFlowData,
        periods: int = 6,
        scenario: ForecastScenario = ForecastScenario.BASELINE
    ) -> ForecastResult:
        """
        Generate cash flow forecast.

        Args:
            data: Historical cash flow data
            periods: Number of periods to forecast (months)
            scenario: Forecast scenario

        Returns:
            ForecastResult with predictions and analysis
        """
        if len(data.dates) < 3:
            raise ValueError("Need at least 3 data points for forecasting")

        # Apply scenario adjustments to historical trends
        adjusted_data = self._apply_scenario(data, scenario)

        if self.use_prophet:
            return self._forecast_prophet(adjusted_data, periods, scenario)
        else:
            return self._forecast_statistical(adjusted_data, periods, scenario)

    def _apply_scenario(
        self,
        data: CashFlowData,
        scenario: ForecastScenario
    ) -> CashFlowData:
        """Apply scenario adjustments to data for trend projection"""
        if scenario == ForecastScenario.BASELINE:
            return data

        # Calculate adjustment factors
        if scenario == ForecastScenario.OPTIMISTIC:
            inflow_factor = 1.20   # +20% revenue
            outflow_factor = 0.90  # -10% expenses
        elif scenario == ForecastScenario.PESSIMISTIC:
            inflow_factor = 0.80   # -20% revenue
            outflow_factor = 1.10  # +10% expenses
        elif scenario == ForecastScenario.GROWTH:
            inflow_factor = 1.30   # +30% revenue
            outflow_factor = 1.15  # +15% expenses (investment)
        elif scenario == ForecastScenario.COST_CUTTING:
            inflow_factor = 1.0    # No revenue change
            outflow_factor = 0.80  # -20% expenses
        else:
            return data

        # Adjust recent data trends (last 3 months influence forecast)
        adjusted_inflows = data.cash_inflows.copy()
        adjusted_outflows = data.cash_outflows.copy()

        # Apply gradual adjustment to recent periods
        n = min(3, len(data.dates))
        for i in range(n):
            weight = (i + 1) / n  # Gradual adjustment
            idx = -(n - i)
            adjusted_inflows[idx] *= (1 + (inflow_factor - 1) * weight)
            adjusted_outflows[idx] *= (1 + (outflow_factor - 1) * weight)

        # Recalculate balances
        adjusted_balances = data.cash_balances.copy()
        if len(adjusted_balances) > 1:
            for i in range(1, len(adjusted_balances)):
                net = adjusted_inflows[i] - adjusted_outflows[i]
                adjusted_balances[i] = adjusted_balances[i-1] + net

        return CashFlowData(
            dates=data.dates,
            cash_inflows=adjusted_inflows,
            cash_outflows=adjusted_outflows,
            cash_balances=adjusted_balances
        )

    def _forecast_prophet(
        self,
        data: CashFlowData,
        periods: int,
        scenario: ForecastScenario
    ) -> ForecastResult:
        """Forecast using Prophet"""
        import pandas as pd

        # Prepare data for Prophet
        df = pd.DataFrame(data.to_dataframe_format())

        # Configure Prophet
        model = Prophet(
            interval_width=self.confidence_level,
            yearly_seasonality=True if len(data.dates) >= 12 else False,
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode='multiplicative'
        )

        # Fit model
        model.fit(df)

        # Create future dataframe
        future = model.make_future_dataframe(periods=periods, freq='MS')

        # Predict
        forecast = model.predict(future)

        # Extract forecast portion
        forecast_df = forecast.tail(periods)

        forecast_dates = forecast_df['ds'].tolist()
        predicted_cash = forecast_df['yhat'].tolist()
        lower_bound = forecast_df['yhat_lower'].tolist()
        upper_bound = forecast_df['yhat_upper'].tolist()

        # Calculate runway
        runway, zero_date = self._calculate_runway(
            data.cash_balances[-1],
            predicted_cash,
            forecast_dates
        )

        return ForecastResult(
            forecast_dates=forecast_dates,
            predicted_cash=[round(p, 2) for p in predicted_cash],
            lower_bound=[round(l, 2) for l in lower_bound],
            upper_bound=[round(u, 2) for u in upper_bound],
            confidence_level=self.confidence_level,
            runway_months=runway,
            zero_cash_date=zero_date,
            scenario=scenario,
            model_type="prophet",
            metrics={
                "historical_periods": len(data.dates),
                "forecast_periods": periods
            }
        )

    def _forecast_statistical(
        self,
        data: CashFlowData,
        periods: int,
        scenario: ForecastScenario
    ) -> ForecastResult:
        """Forecast using statistical methods (fallback)"""
        # Calculate recent trends
        net_flows = data.net_cash_flow

        # Use weighted moving average for trend
        recent = net_flows[-min(6, len(net_flows)):]
        weights = list(range(1, len(recent) + 1))
        weighted_avg = sum(f * w for f, w in zip(recent, weights)) / sum(weights)

        # Calculate volatility for confidence intervals
        if len(net_flows) > 2:
            std_dev = np.std(net_flows)
        else:
            std_dev = abs(weighted_avg) * 0.2  # Assume 20% volatility

        # Generate forecast
        last_date = data.dates[-1]
        last_cash = data.cash_balances[-1]

        forecast_dates = []
        predicted_cash = []
        lower_bound = []
        upper_bound = []

        current_cash = last_cash
        z_score = 1.28 if self.confidence_level == 0.80 else 1.96  # 80% or 95%

        for i in range(periods):
            # Next month
            next_date = last_date + timedelta(days=30 * (i + 1))
            forecast_dates.append(next_date)

            # Project cash
            current_cash += weighted_avg
            predicted_cash.append(round(current_cash, 2))

            # Confidence interval widens over time
            interval_width = z_score * std_dev * np.sqrt(i + 1)
            lower_bound.append(round(current_cash - interval_width, 2))
            upper_bound.append(round(current_cash + interval_width, 2))

        # Calculate runway
        runway, zero_date = self._calculate_runway(
            last_cash,
            predicted_cash,
            forecast_dates
        )

        return ForecastResult(
            forecast_dates=forecast_dates,
            predicted_cash=predicted_cash,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=self.confidence_level,
            runway_months=runway,
            zero_cash_date=zero_date,
            scenario=scenario,
            model_type="statistical",
            metrics={
                "weighted_avg_flow": round(weighted_avg, 2),
                "std_dev": round(std_dev, 2),
                "historical_periods": len(data.dates),
                "forecast_periods": periods
            }
        )

    def _calculate_runway(
        self,
        current_cash: float,
        forecast: List[float],
        dates: List[datetime]
    ) -> Tuple[float, Optional[datetime]]:
        """Calculate cash runway and zero-cash date"""
        # Find when cash goes negative
        for i, (cash, date) in enumerate(zip(forecast, dates)):
            if cash <= 0:
                # Interpolate exact date
                if i > 0:
                    prev_cash = current_cash if i == 0 else forecast[i-1]
                    days_diff = (dates[i] - dates[i-1]).days if i > 0 else 30
                    if prev_cash != cash:
                        ratio = prev_cash / (prev_cash - cash)
                        zero_date = dates[i-1] + timedelta(days=int(days_diff * ratio))
                        runway = (zero_date - datetime.now()).days / 30
                        return max(0, runway), zero_date

                runway = i
                return runway, dates[i]

        # Cash doesn't go negative in forecast
        return len(forecast), None

    def multi_scenario_forecast(
        self,
        data: CashFlowData,
        periods: int = 6
    ) -> Dict[str, ForecastResult]:
        """
        Generate forecasts for all scenarios.

        Args:
            data: Historical cash flow data
            periods: Forecast periods

        Returns:
            Dict mapping scenario names to ForecastResults
        """
        results = {}

        for scenario in ForecastScenario:
            try:
                result = self.forecast(data, periods, scenario)
                results[scenario.value] = result
            except Exception as e:
                logger.error(f"Error forecasting {scenario.value}: {e}")

        return results

    def calculate_burn_rate(self, data: CashFlowData) -> Dict[str, Any]:
        """
        Calculate burn rate metrics.

        Returns:
            Dict with burn rate analysis
        """
        net_flows = data.net_cash_flow

        # Monthly burn (negative net flow)
        burns = [f for f in net_flows if f < 0]
        avg_burn = abs(np.mean(burns)) if burns else 0

        # Gross burn (total outflows)
        avg_outflow = np.mean(data.cash_outflows)

        # Current cash
        current_cash = data.cash_balances[-1]

        # Runway calculation
        if avg_burn > 0:
            runway_net = current_cash / avg_burn
        else:
            runway_net = float('inf')

        runway_gross = current_cash / avg_outflow if avg_outflow > 0 else float('inf')

        return {
            "net_burn_rate": round(avg_burn, 2),
            "gross_burn_rate": round(avg_outflow, 2),
            "current_cash": round(current_cash, 2),
            "runway_months_net": round(runway_net, 1) if runway_net != float('inf') else None,
            "runway_months_gross": round(runway_gross, 1) if runway_gross != float('inf') else None,
            "burn_trend": self._calculate_trend(burns) if burns else "stable"
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """Determine if values are trending up, down, or stable"""
        if len(values) < 2:
            return "stable"

        # Simple linear regression slope
        x = list(range(len(values)))
        x_mean = np.mean(x)
        y_mean = np.mean(values)

        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, values))
        denominator = sum((xi - x_mean) ** 2 for xi in x)

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Threshold for trend detection (5% of mean)
        threshold = abs(y_mean) * 0.05

        if slope > threshold:
            return "increasing"
        elif slope < -threshold:
            return "decreasing"
        else:
            return "stable"
