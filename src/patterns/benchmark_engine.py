"""
Benchmark Engine Pattern - Cash Flow Intelligence

A KPI benchmarking system that compares SMB financial metrics against
industry standards. Generates gap analysis, scores, and recommendations.

Use cases:
- SMB financial benchmarking
- Cash flow KPI tracking
- Industry comparison reports
- Performance gap analysis
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class KPIDirection(Enum):
    """Whether higher or lower values are better."""
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


class KPICategory(Enum):
    """Categories for organizing KPIs."""
    LIQUIDITY = "Liquidity"
    PROFITABILITY = "Profitability"
    EFFICIENCY = "Efficiency"
    LEVERAGE = "Leverage"
    GROWTH = "Growth"
    CASH_FLOW = "Cash Flow"
    WORKING_CAPITAL = "Working Capital"
    CUSTOM = "Custom"


@dataclass
class KPIDefinition:
    """Definition of a Key Performance Indicator."""
    kpi_id: str
    name: str
    benchmark_value: float
    direction: KPIDirection = KPIDirection.HIGHER_IS_BETTER
    category: KPICategory = KPICategory.CUSTOM
    unit: str = ""
    description: str = ""
    weight: float = 1.0
    threshold_excellent: Optional[float] = None
    threshold_poor: Optional[float] = None


@dataclass
class KPIScore:
    """Score for a single KPI."""
    kpi_id: str
    kpi_name: str
    actual_value: float
    benchmark_value: float
    score: float  # 0-100
    gap: float
    gap_percent: float
    direction: KPIDirection
    rating: str  # "Excellent", "Good", "Fair", "Poor", "Critical"
    unit: str = ""
    recommendation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kpi_id": self.kpi_id,
            "kpi_name": self.kpi_name,
            "actual_value": self.actual_value,
            "benchmark_value": self.benchmark_value,
            "score": self.score,
            "gap": self.gap,
            "gap_percent": self.gap_percent,
            "direction": self.direction.value,
            "rating": self.rating,
            "unit": self.unit,
            "recommendation": self.recommendation,
            "metadata": self.metadata
        }


@dataclass
class CategoryScore:
    """Aggregated score for a category of KPIs."""
    category: str
    score: float
    kpi_count: int
    kpi_scores: List[KPIScore]
    strengths: List[str]
    improvements: List[str]


@dataclass
class BenchmarkReport:
    """Complete benchmark analysis report."""
    entity_id: str
    overall_score: float
    overall_rating: str
    grade: str
    category_scores: Dict[str, CategoryScore]
    kpi_scores: List[KPIScore]
    top_strengths: List[str]
    top_improvements: List[str]
    recommendations: List[str]
    percentile: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "overall_score": self.overall_score,
            "overall_rating": self.overall_rating,
            "grade": self.grade,
            "category_scores": {
                cat: {
                    "score": cs.score,
                    "kpi_count": cs.kpi_count,
                    "strengths": cs.strengths,
                    "improvements": cs.improvements
                }
                for cat, cs in self.category_scores.items()
            },
            "kpi_count": len(self.kpi_scores),
            "top_strengths": self.top_strengths,
            "top_improvements": self.top_improvements,
            "recommendations": self.recommendations,
            "percentile": self.percentile
        }


class BenchmarkEngine:
    """
    KPI benchmarking engine for SMB financial analysis.

    Example:
    ```python
    kpis = [
        KPIDefinition("current_ratio", "Current Ratio", 1.5,
                     KPIDirection.HIGHER_IS_BETTER, KPICategory.LIQUIDITY),
        KPIDefinition("gross_margin", "Gross Margin", 35.0,
                     KPIDirection.HIGHER_IS_BETTER, KPICategory.PROFITABILITY, "%"),
        KPIDefinition("dso", "Days Sales Outstanding", 45.0,
                     KPIDirection.LOWER_IS_BETTER, KPICategory.EFFICIENCY, "days"),
    ]

    engine = BenchmarkEngine(kpis)

    report = engine.analyze({
        "current_ratio": 1.8,
        "gross_margin": 32,
        "dso": 52
    }, entity_id="SMB-001")

    print(f"Overall Score: {report.overall_score}")
    print(f"Grade: {report.grade}")
    ```
    """

    RATING_THRESHOLDS = {
        90: "Excellent",
        75: "Good",
        60: "Fair",
        40: "Poor",
        0: "Critical"
    }

    GRADE_THRESHOLDS = {
        90: "A",
        80: "B",
        70: "C",
        60: "D",
        0: "F"
    }

    def __init__(
        self,
        kpis: List[KPIDefinition],
        category_weights: Optional[Dict[str, float]] = None
    ):
        self.kpis = {kpi.kpi_id: kpi for kpi in kpis}
        self.category_weights = category_weights or {}

        self.kpis_by_category: Dict[str, List[KPIDefinition]] = {}
        for kpi in kpis:
            cat = kpi.category.value
            if cat not in self.kpis_by_category:
                self.kpis_by_category[cat] = []
            self.kpis_by_category[cat].append(kpi)

    def score_kpi(
        self,
        kpi: KPIDefinition,
        actual_value: float
    ) -> KPIScore:
        """Score a single KPI against its benchmark."""
        benchmark = kpi.benchmark_value

        gap = actual_value - benchmark

        if benchmark != 0:
            gap_percent = (gap / abs(benchmark)) * 100
        else:
            gap_percent = 100 if actual_value > 0 else 0

        score = self._calculate_score(actual_value, benchmark, kpi.direction)
        rating = self._determine_rating(score)
        recommendation = self._generate_recommendation(kpi, actual_value, benchmark, rating)

        return KPIScore(
            kpi_id=kpi.kpi_id,
            kpi_name=kpi.name,
            actual_value=round(actual_value, 2),
            benchmark_value=benchmark,
            score=round(score, 1),
            gap=round(gap, 2),
            gap_percent=round(gap_percent, 1),
            direction=kpi.direction,
            rating=rating,
            unit=kpi.unit,
            recommendation=recommendation,
            metadata={
                "category": kpi.category.value,
                "weight": kpi.weight,
                "description": kpi.description
            }
        )

    def _calculate_score(
        self,
        actual: float,
        benchmark: float,
        direction: KPIDirection
    ) -> float:
        """Calculate score based on actual vs benchmark."""
        if benchmark == 0:
            return 100 if actual >= 0 else 0

        if direction == KPIDirection.HIGHER_IS_BETTER:
            if actual >= benchmark:
                bonus = min(20, ((actual - benchmark) / benchmark) * 20)
                return min(120, 100 + bonus)
            else:
                return max(0, (actual / benchmark) * 100)
        else:  # LOWER_IS_BETTER
            if actual <= benchmark:
                if actual == 0:
                    return 120
                bonus = min(20, ((benchmark - actual) / benchmark) * 20)
                return min(120, 100 + bonus)
            else:
                excess_ratio = actual / benchmark
                return max(0, 100 - ((excess_ratio - 1) * 100))

    def _determine_rating(self, score: float) -> str:
        """Determine rating from score."""
        for threshold, rating in sorted(self.RATING_THRESHOLDS.items(), reverse=True):
            if score >= threshold:
                return rating
        return "Critical"

    def _determine_grade(self, score: float) -> str:
        """Determine letter grade from score."""
        for threshold, grade in sorted(self.GRADE_THRESHOLDS.items(), reverse=True):
            if score >= threshold:
                return grade
        return "F"

    def _generate_recommendation(
        self,
        kpi: KPIDefinition,
        actual: float,
        benchmark: float,
        rating: str
    ) -> str:
        """Generate improvement recommendation."""
        if rating in ["Excellent", "Good"]:
            return f"Maintain current performance in {kpi.name}"

        direction_text = "increase" if kpi.direction == KPIDirection.HIGHER_IS_BETTER else "reduce"
        gap = abs(actual - benchmark)

        if rating == "Fair":
            return f"Minor improvement needed: {direction_text} {kpi.name} by {gap:.1f}{kpi.unit}"
        elif rating == "Poor":
            return f"Priority action: {direction_text} {kpi.name} significantly (gap: {gap:.1f}{kpi.unit})"
        else:
            return f"CRITICAL: Immediate intervention required for {kpi.name}"

    def analyze(
        self,
        actual_values: Dict[str, float],
        entity_id: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ) -> BenchmarkReport:
        """Perform complete benchmark analysis."""
        kpi_scores = []
        category_kpis: Dict[str, List[KPIScore]] = {}

        for kpi_id, kpi in self.kpis.items():
            actual = actual_values.get(kpi_id)
            if actual is None:
                logger.warning(f"Missing value for KPI '{kpi_id}'")
                continue

            score = self.score_kpi(kpi, actual)
            kpi_scores.append(score)

            cat = kpi.category.value
            if cat not in category_kpis:
                category_kpis[cat] = []
            category_kpis[cat].append(score)

        category_scores = {}
        for cat, scores in category_kpis.items():
            cat_score = self._calculate_category_score(cat, scores)
            category_scores[cat] = cat_score

        overall_score = self._calculate_overall_score(category_scores)
        overall_rating = self._determine_rating(overall_score)
        grade = self._determine_grade(overall_score)

        sorted_kpis = sorted(kpi_scores, key=lambda k: k.score, reverse=True)
        top_strengths = [
            f"{k.kpi_name}: {k.actual_value}{k.unit} ({k.rating})"
            for k in sorted_kpis[:3] if k.rating in ["Excellent", "Good"]
        ]
        top_improvements = [
            f"{k.kpi_name}: {k.actual_value}{k.unit} vs benchmark {k.benchmark_value}{k.unit}"
            for k in sorted_kpis[-3:] if k.rating in ["Poor", "Critical"]
        ]

        recommendations = [k.recommendation for k in kpi_scores if k.rating in ["Poor", "Critical"]]

        return BenchmarkReport(
            entity_id=entity_id,
            overall_score=round(overall_score, 1),
            overall_rating=overall_rating,
            grade=grade,
            category_scores=category_scores,
            kpi_scores=kpi_scores,
            top_strengths=top_strengths,
            top_improvements=top_improvements,
            recommendations=recommendations[:5],
            metadata=metadata or {}
        )

    def _calculate_category_score(
        self,
        category: str,
        kpi_scores: List[KPIScore]
    ) -> CategoryScore:
        """Calculate aggregated category score."""
        if not kpi_scores:
            return CategoryScore(
                category=category,
                score=0,
                kpi_count=0,
                kpi_scores=[],
                strengths=[],
                improvements=[]
            )

        total_weight = sum(k.metadata.get("weight", 1) for k in kpi_scores)
        weighted_sum = sum(
            k.score * k.metadata.get("weight", 1) for k in kpi_scores
        )
        avg_score = weighted_sum / total_weight if total_weight > 0 else 0

        strengths = [k.kpi_name for k in kpi_scores if k.rating in ["Excellent", "Good"]]
        improvements = [k.kpi_name for k in kpi_scores if k.rating in ["Poor", "Critical"]]

        return CategoryScore(
            category=category,
            score=round(avg_score, 1),
            kpi_count=len(kpi_scores),
            kpi_scores=kpi_scores,
            strengths=strengths,
            improvements=improvements
        )

    def _calculate_overall_score(
        self,
        category_scores: Dict[str, CategoryScore]
    ) -> float:
        """Calculate overall score from category scores."""
        if not category_scores:
            return 0

        total_weight = 0
        weighted_sum = 0

        for cat, cat_score in category_scores.items():
            weight = self.category_weights.get(cat, 1.0)
            weighted_sum += cat_score.score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0

    def compare_entities(
        self,
        entities: List[Dict[str, Any]],
        id_field: str = "id"
    ) -> List[BenchmarkReport]:
        """Compare multiple entities against benchmarks."""
        reports = []
        for entity in entities:
            entity_id = str(entity.get(id_field, "unknown"))
            values = {k: v for k, v in entity.items() if k in self.kpis}

            report = self.analyze(values, entity_id=entity_id)
            reports.append(report)

        reports.sort(key=lambda r: r.overall_score, reverse=True)

        for i, report in enumerate(reports):
            report.percentile = round((1 - (i / len(reports))) * 100, 1)

        return reports

    def get_kpi_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all configured KPIs."""
        return [
            {
                "kpi_id": kpi.kpi_id,
                "name": kpi.name,
                "category": kpi.category.value,
                "benchmark": kpi.benchmark_value,
                "unit": kpi.unit,
                "direction": kpi.direction.value,
                "weight": kpi.weight,
                "description": kpi.description
            }
            for kpi in self.kpis.values()
        ]


# =============================================================================
# Factory Functions for Cash Flow Intelligence
# =============================================================================

def create_smb_financial_benchmarks() -> BenchmarkEngine:
    """Create comprehensive SMB financial benchmark engine."""
    kpis = [
        # Liquidity KPIs
        KPIDefinition("current_ratio", "Current Ratio",
                     1.5, KPIDirection.HIGHER_IS_BETTER, KPICategory.LIQUIDITY, "",
                     "Current assets / Current liabilities (target: 1.5-2.0)"),
        KPIDefinition("quick_ratio", "Quick Ratio",
                     1.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.LIQUIDITY, "",
                     "Liquid assets / Current liabilities (target: 1.0+)"),
        KPIDefinition("cash_ratio", "Cash Ratio",
                     0.2, KPIDirection.HIGHER_IS_BETTER, KPICategory.LIQUIDITY, "",
                     "Cash / Current liabilities"),

        # Profitability KPIs
        KPIDefinition("gross_margin", "Gross Profit Margin",
                     35.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.PROFITABILITY, "%",
                     "Gross profit / Revenue"),
        KPIDefinition("operating_margin", "Operating Profit Margin",
                     10.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.PROFITABILITY, "%",
                     "Operating income / Revenue"),
        KPIDefinition("net_margin", "Net Profit Margin",
                     5.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.PROFITABILITY, "%",
                     "Net income / Revenue"),
        KPIDefinition("roa", "Return on Assets",
                     8.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.PROFITABILITY, "%",
                     "Net income / Total assets"),
        KPIDefinition("roe", "Return on Equity",
                     15.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.PROFITABILITY, "%",
                     "Net income / Shareholders equity"),

        # Efficiency KPIs
        KPIDefinition("asset_turnover", "Asset Turnover Ratio",
                     1.5, KPIDirection.HIGHER_IS_BETTER, KPICategory.EFFICIENCY, "x",
                     "Revenue / Average total assets"),
        KPIDefinition("inventory_turnover", "Inventory Turnover",
                     6.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.EFFICIENCY, "x/year",
                     "COGS / Average inventory"),
        KPIDefinition("receivables_turnover", "Receivables Turnover",
                     8.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.EFFICIENCY, "x/year",
                     "Revenue / Average receivables"),

        # Leverage KPIs
        KPIDefinition("debt_to_equity", "Debt to Equity",
                     1.5, KPIDirection.LOWER_IS_BETTER, KPICategory.LEVERAGE, "",
                     "Total debt / Shareholders equity"),
        KPIDefinition("debt_to_assets", "Debt to Assets",
                     0.5, KPIDirection.LOWER_IS_BETTER, KPICategory.LEVERAGE, "",
                     "Total debt / Total assets"),
        KPIDefinition("interest_coverage", "Interest Coverage Ratio",
                     3.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.LEVERAGE, "x",
                     "EBIT / Interest expense"),

        # Growth KPIs
        KPIDefinition("revenue_growth", "Revenue Growth Rate",
                     10.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.GROWTH, "%",
                     "Year-over-year revenue growth"),
        KPIDefinition("earnings_growth", "Earnings Growth Rate",
                     12.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.GROWTH, "%",
                     "Year-over-year earnings growth"),
    ]

    return BenchmarkEngine(
        kpis,
        category_weights={
            "Liquidity": 1.2,
            "Profitability": 1.1,
            "Efficiency": 1.0,
            "Leverage": 1.0,
            "Growth": 0.9
        }
    )


def create_cash_flow_benchmarks() -> BenchmarkEngine:
    """Create cash-flow focused benchmark engine for SMBs."""
    kpis = [
        # Cash Flow KPIs
        KPIDefinition("days_cash_on_hand", "Days Cash on Hand",
                     45.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.CASH_FLOW, "days",
                     "Cash / (Operating expenses / 365)"),
        KPIDefinition("operating_cash_ratio", "Operating Cash Flow Ratio",
                     0.4, KPIDirection.HIGHER_IS_BETTER, KPICategory.CASH_FLOW, "",
                     "Operating cash flow / Current liabilities"),
        KPIDefinition("cash_flow_margin", "Cash Flow Margin",
                     8.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.CASH_FLOW, "%",
                     "Operating cash flow / Revenue"),
        KPIDefinition("free_cash_flow_yield", "Free Cash Flow Yield",
                     5.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.CASH_FLOW, "%",
                     "Free cash flow / Market cap (or equity)"),

        # Working Capital KPIs
        KPIDefinition("dso", "Days Sales Outstanding",
                     45.0, KPIDirection.LOWER_IS_BETTER, KPICategory.WORKING_CAPITAL, "days",
                     "Average days to collect receivables"),
        KPIDefinition("dpo", "Days Payables Outstanding",
                     30.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.WORKING_CAPITAL, "days",
                     "Average days to pay suppliers"),
        KPIDefinition("dio", "Days Inventory Outstanding",
                     60.0, KPIDirection.LOWER_IS_BETTER, KPICategory.WORKING_CAPITAL, "days",
                     "Average days inventory held"),
        KPIDefinition("cash_conversion_cycle", "Cash Conversion Cycle",
                     75.0, KPIDirection.LOWER_IS_BETTER, KPICategory.WORKING_CAPITAL, "days",
                     "DSO + DIO - DPO"),
        KPIDefinition("working_capital_ratio", "Working Capital Ratio",
                     0.2, KPIDirection.HIGHER_IS_BETTER, KPICategory.WORKING_CAPITAL, "",
                     "Working capital / Revenue"),

        # Burn Rate KPIs (for startups/growth companies)
        KPIDefinition("burn_rate", "Monthly Burn Rate",
                     10.0, KPIDirection.LOWER_IS_BETTER, KPICategory.CASH_FLOW, "%",
                     "Monthly cash decrease as % of reserves"),
        KPIDefinition("runway_months", "Cash Runway",
                     12.0, KPIDirection.HIGHER_IS_BETTER, KPICategory.CASH_FLOW, "months",
                     "Months of operations with current cash"),
    ]

    return BenchmarkEngine(
        kpis,
        category_weights={
            "Cash Flow": 1.3,
            "Working Capital": 1.1
        }
    )
