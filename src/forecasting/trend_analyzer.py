"""
Trend Analyzer for Cash Flow Intelligence

Analyzes historical financial data to identify patterns, seasonality,
and trends that inform cash flow management.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """Direction of trend"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class SeasonalPattern(Enum):
    """Types of seasonal patterns"""
    NONE = "none"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"


@dataclass
class TrendResult:
    """Result of trend analysis"""
    metric_name: str
    direction: TrendDirection
    slope: float
    r_squared: float
    seasonality: SeasonalPattern
    seasonal_factors: Dict[int, float]
    volatility: float
    recent_change: float  # % change recent vs historical
    anomalies: List[Dict[str, Any]]
    insights: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "direction": self.direction.value,
            "slope": self.slope,
            "r_squared": self.r_squared,
            "seasonality": self.seasonality.value,
            "seasonal_factors": self.seasonal_factors,
            "volatility": self.volatility,
            "recent_change": self.recent_change,
            "anomalies": self.anomalies,
            "insights": self.insights
        }


class TrendAnalyzer:
    """
    Analyzes financial time series for trends, seasonality, and anomalies.

    Provides:
    - Linear trend detection
    - Seasonality identification
    - Anomaly detection
    - Pattern insights

    Example:
    ```python
    analyzer = TrendAnalyzer()

    result = analyzer.analyze(
        values=[100, 95, 110, 105, 120, 115, 130],
        dates=[date1, date2, ...],
        metric_name="revenue"
    )

    print(f"Trend: {result.direction.value}")
    print(f"Seasonality: {result.seasonality.value}")
    ```
    """

    def __init__(
        self,
        anomaly_threshold: float = 2.0,  # Standard deviations
        min_seasonality_periods: int = 12
    ):
        """
        Initialize analyzer.

        Args:
            anomaly_threshold: Z-score threshold for anomaly detection
            min_seasonality_periods: Minimum data points for seasonality
        """
        self.anomaly_threshold = anomaly_threshold
        self.min_seasonality_periods = min_seasonality_periods

    def analyze(
        self,
        values: List[float],
        dates: List[datetime],
        metric_name: str = "metric"
    ) -> TrendResult:
        """
        Perform comprehensive trend analysis.

        Args:
            values: Time series values
            dates: Corresponding dates
            metric_name: Name of the metric being analyzed

        Returns:
            TrendResult with analysis
        """
        if len(values) < 3:
            return self._minimal_result(values, metric_name)

        # Trend analysis
        direction, slope, r_squared = self._analyze_trend(values)

        # Seasonality detection
        seasonality, seasonal_factors = self._detect_seasonality(values, dates)

        # Volatility
        volatility = self._calculate_volatility(values)

        # Recent change
        recent_change = self._calculate_recent_change(values)

        # Anomaly detection
        anomalies = self._detect_anomalies(values, dates)

        # Generate insights
        insights = self._generate_insights(
            metric_name, direction, slope, seasonality,
            volatility, recent_change, anomalies
        )

        return TrendResult(
            metric_name=metric_name,
            direction=direction,
            slope=round(slope, 4),
            r_squared=round(r_squared, 4),
            seasonality=seasonality,
            seasonal_factors=seasonal_factors,
            volatility=round(volatility, 4),
            recent_change=round(recent_change, 2),
            anomalies=anomalies,
            insights=insights
        )

    def _analyze_trend(
        self,
        values: List[float]
    ) -> Tuple[TrendDirection, float, float]:
        """Analyze linear trend using regression"""
        n = len(values)
        x = np.array(range(n))
        y = np.array(values)

        # Linear regression
        x_mean = np.mean(x)
        y_mean = np.mean(y)

        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if denominator == 0:
            return TrendDirection.STABLE, 0.0, 0.0

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # R-squared
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Determine direction
        volatility = np.std(values) / abs(y_mean) if y_mean != 0 else 0

        if volatility > 0.3:  # High volatility
            direction = TrendDirection.VOLATILE
        elif abs(slope) < abs(y_mean) * 0.01:  # <1% of mean per period
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING

        return direction, slope, r_squared

    def _detect_seasonality(
        self,
        values: List[float],
        dates: List[datetime]
    ) -> Tuple[SeasonalPattern, Dict[int, float]]:
        """Detect seasonal patterns"""
        if len(values) < self.min_seasonality_periods:
            return SeasonalPattern.NONE, {}

        # Calculate mean
        mean_val = np.mean(values)
        if mean_val == 0:
            return SeasonalPattern.NONE, {}

        # Check monthly seasonality (by month number)
        monthly_factors = {}
        try:
            months_data: Dict[int, List[float]] = {}
            for date, value in zip(dates, values):
                month = date.month
                if month not in months_data:
                    months_data[month] = []
                months_data[month].append(value)

            if len(months_data) >= 4:
                for month, month_values in months_data.items():
                    if month_values:
                        monthly_factors[month] = np.mean(month_values) / mean_val

                # Check if seasonality is significant
                factor_variance = np.var(list(monthly_factors.values()))
                if factor_variance > 0.01:  # >10% variance in factors
                    return SeasonalPattern.MONTHLY, monthly_factors

        except Exception as e:
            logger.warning(f"Error detecting seasonality: {e}")

        return SeasonalPattern.NONE, {}

    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate coefficient of variation"""
        mean_val = np.mean(values)
        if mean_val == 0:
            return 0.0
        return np.std(values) / abs(mean_val)

    def _calculate_recent_change(
        self,
        values: List[float],
        recent_periods: int = 3
    ) -> float:
        """Calculate % change between recent and historical average"""
        if len(values) < recent_periods + 3:
            return 0.0

        historical = values[:-recent_periods]
        recent = values[-recent_periods:]

        hist_avg = np.mean(historical)
        recent_avg = np.mean(recent)

        if hist_avg == 0:
            return 0.0

        return ((recent_avg - hist_avg) / abs(hist_avg)) * 100

    def _detect_anomalies(
        self,
        values: List[float],
        dates: List[datetime]
    ) -> List[Dict[str, Any]]:
        """Detect anomalous values using z-score"""
        anomalies = []

        mean_val = np.mean(values)
        std_val = np.std(values)

        if std_val == 0:
            return []

        for i, (value, date) in enumerate(zip(values, dates)):
            z_score = (value - mean_val) / std_val

            if abs(z_score) > self.anomaly_threshold:
                anomalies.append({
                    "index": i,
                    "date": date.isoformat(),
                    "value": value,
                    "z_score": round(z_score, 2),
                    "type": "high" if z_score > 0 else "low"
                })

        return anomalies

    def _generate_insights(
        self,
        metric_name: str,
        direction: TrendDirection,
        slope: float,
        seasonality: SeasonalPattern,
        volatility: float,
        recent_change: float,
        anomalies: List[Dict]
    ) -> List[str]:
        """Generate human-readable insights"""
        insights = []

        # Trend insight
        if direction == TrendDirection.INCREASING:
            insights.append(f"{metric_name} shows an upward trend (+{abs(slope):.1f} per period)")
        elif direction == TrendDirection.DECREASING:
            insights.append(f"{metric_name} shows a downward trend (-{abs(slope):.1f} per period)")
        elif direction == TrendDirection.VOLATILE:
            insights.append(f"{metric_name} shows high volatility - consider stabilization measures")
        else:
            insights.append(f"{metric_name} is relatively stable")

        # Seasonality insight
        if seasonality == SeasonalPattern.MONTHLY:
            insights.append(f"{metric_name} exhibits monthly seasonal patterns - factor this into forecasts")

        # Volatility insight
        if volatility > 0.3:
            insights.append(f"High volatility ({volatility:.0%}) indicates unpredictability - build larger cash buffers")
        elif volatility < 0.1:
            insights.append(f"Low volatility ({volatility:.0%}) indicates predictable {metric_name}")

        # Recent change insight
        if abs(recent_change) > 10:
            direction_word = "increased" if recent_change > 0 else "decreased"
            insights.append(f"Recent {metric_name} has {direction_word} {abs(recent_change):.0f}% vs historical average")

        # Anomaly insight
        if anomalies:
            insights.append(f"Detected {len(anomalies)} unusual data point(s) - investigate for data quality or exceptional events")

        return insights

    def _minimal_result(
        self,
        values: List[float],
        metric_name: str
    ) -> TrendResult:
        """Return minimal result for insufficient data"""
        return TrendResult(
            metric_name=metric_name,
            direction=TrendDirection.STABLE,
            slope=0.0,
            r_squared=0.0,
            seasonality=SeasonalPattern.NONE,
            seasonal_factors={},
            volatility=0.0,
            recent_change=0.0,
            anomalies=[],
            insights=["Insufficient data for comprehensive analysis"]
        )

    def analyze_multiple(
        self,
        data: Dict[str, Tuple[List[float], List[datetime]]]
    ) -> Dict[str, TrendResult]:
        """
        Analyze multiple metrics at once.

        Args:
            data: Dict mapping metric names to (values, dates) tuples

        Returns:
            Dict mapping metric names to TrendResults
        """
        results = {}

        for metric_name, (values, dates) in data.items():
            try:
                results[metric_name] = self.analyze(values, dates, metric_name)
            except Exception as e:
                logger.error(f"Error analyzing {metric_name}: {e}")
                results[metric_name] = self._minimal_result([], metric_name)

        return results

    def compare_periods(
        self,
        current_values: List[float],
        previous_values: List[float],
        metric_name: str = "metric"
    ) -> Dict[str, Any]:
        """
        Compare current period to previous period.

        Args:
            current_values: Values for current period
            previous_values: Values for previous period
            metric_name: Name of metric

        Returns:
            Comparison analysis
        """
        current_sum = sum(current_values)
        previous_sum = sum(previous_values)

        current_avg = np.mean(current_values) if current_values else 0
        previous_avg = np.mean(previous_values) if previous_values else 0

        if previous_sum == 0:
            pct_change = 0
        else:
            pct_change = ((current_sum - previous_sum) / abs(previous_sum)) * 100

        return {
            "metric_name": metric_name,
            "current_total": round(current_sum, 2),
            "previous_total": round(previous_sum, 2),
            "current_average": round(current_avg, 2),
            "previous_average": round(previous_avg, 2),
            "absolute_change": round(current_sum - previous_sum, 2),
            "percent_change": round(pct_change, 2),
            "trend": "up" if pct_change > 5 else "down" if pct_change < -5 else "flat"
        }
