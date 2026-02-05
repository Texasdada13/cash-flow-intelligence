"""
Weighted Scoring Pattern - Cash Flow Intelligence

A flexible, configurable multi-component scoring engine for SMB financial health.
Calculates weighted aggregate scores from multiple financial metrics.

Use cases:
- SMB financial health scores
- Cash flow quality assessment
- Working capital efficiency
- Profitability ratings
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ScoreDirection(Enum):
    """Whether higher values are better or worse."""
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


@dataclass
class ScoreComponent:
    """Definition of a single scoring component."""
    name: str
    weight: float  # 0.0 to 1.0, all weights should sum to 1.0
    direction: ScoreDirection = ScoreDirection.HIGHER_IS_BETTER
    min_value: float = 0.0
    max_value: float = 100.0
    description: str = ""

    def normalize(self, value: float) -> float:
        """Normalize a value to 0-100 scale."""
        if self.max_value == self.min_value:
            return 100.0 if value >= self.max_value else 0.0

        value = max(self.min_value, min(self.max_value, value))
        normalized = ((value - self.min_value) / (self.max_value - self.min_value)) * 100

        if self.direction == ScoreDirection.LOWER_IS_BETTER:
            normalized = 100 - normalized

        return round(normalized, 2)


@dataclass
class ScoreResult:
    """Result of scoring an entity."""
    entity_id: str
    overall_score: float
    grade: str
    component_scores: Dict[str, float]
    component_details: Dict[str, Dict[str, Any]]
    risk_level: str
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "overall_score": self.overall_score,
            "grade": self.grade,
            "component_scores": self.component_scores,
            "component_details": self.component_details,
            "risk_level": self.risk_level,
            "recommendations": self.recommendations,
            "metadata": self.metadata
        }


class WeightedScoringEngine:
    """
    A configurable multi-component weighted scoring engine.

    Example for SMB Cash Flow:
    ```python
    components = [
        ScoreComponent("current_ratio", weight=0.25, direction=ScoreDirection.HIGHER_IS_BETTER,
                      min_value=0, max_value=3, description="Current assets / Current liabilities"),
        ScoreComponent("days_cash_on_hand", weight=0.25, direction=ScoreDirection.HIGHER_IS_BETTER,
                      min_value=0, max_value=90, description="Days of operating cash"),
        ScoreComponent("burn_rate", weight=0.25, direction=ScoreDirection.LOWER_IS_BETTER,
                      min_value=0, max_value=50, description="Monthly cash burn percentage"),
        ScoreComponent("receivables_turnover", weight=0.25, direction=ScoreDirection.HIGHER_IS_BETTER,
                      min_value=0, max_value=12, description="Collections efficiency"),
    ]

    engine = WeightedScoringEngine(components)

    result = engine.score({
        "current_ratio": 1.8,
        "days_cash_on_hand": 45,
        "burn_rate": 15,
        "receivables_turnover": 8,
    }, entity_id="SMB-001")

    print(f"Overall Score: {result.overall_score}")
    print(f"Grade: {result.grade}")
    ```
    """

    DEFAULT_GRADE_THRESHOLDS = {
        90: "A",
        80: "B",
        70: "C",
        60: "D",
        0: "F"
    }

    DEFAULT_RISK_THRESHOLDS = {
        80: "Low",
        60: "Medium",
        40: "High",
        0: "Critical"
    }

    def __init__(
        self,
        components: List[ScoreComponent],
        grade_thresholds: Optional[Dict[int, str]] = None,
        risk_thresholds: Optional[Dict[int, str]] = None,
        recommendation_rules: Optional[List[Dict[str, Any]]] = None
    ):
        self.components = {c.name: c for c in components}
        self.grade_thresholds = grade_thresholds or self.DEFAULT_GRADE_THRESHOLDS
        self.risk_thresholds = risk_thresholds or self.DEFAULT_RISK_THRESHOLDS
        self.recommendation_rules = recommendation_rules or []

        total_weight = sum(c.weight for c in components)
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Component weights sum to {total_weight}, not 1.0. Normalizing...")
            for c in components:
                c.weight = c.weight / total_weight

    def score(
        self,
        values: Dict[str, float],
        entity_id: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ScoreResult:
        """Calculate weighted score for an entity."""
        component_scores = {}
        component_details = {}
        weighted_sum = 0.0

        for name, component in self.components.items():
            raw_value = values.get(name)

            if raw_value is None:
                logger.warning(f"Missing value for component '{name}', using min value")
                raw_value = component.min_value

            normalized = component.normalize(raw_value)
            component_scores[name] = normalized

            weighted_contribution = normalized * component.weight
            weighted_sum += weighted_contribution

            component_details[name] = {
                "raw_value": raw_value,
                "normalized_score": normalized,
                "weight": component.weight,
                "weighted_contribution": round(weighted_contribution, 2),
                "direction": component.direction.value,
                "description": component.description
            }

        overall_score = round(weighted_sum, 2)
        grade = self._determine_grade(overall_score)
        risk_level = self._determine_risk_level(overall_score)
        recommendations = self._generate_recommendations(component_scores, overall_score)

        return ScoreResult(
            entity_id=entity_id,
            overall_score=overall_score,
            grade=grade,
            component_scores=component_scores,
            component_details=component_details,
            risk_level=risk_level,
            recommendations=recommendations,
            metadata=metadata or {}
        )

    def score_batch(
        self,
        entities: List[Dict[str, Any]],
        id_field: str = "id",
        value_fields: Optional[List[str]] = None
    ) -> List[ScoreResult]:
        """Score multiple entities at once."""
        results = []
        value_fields = value_fields or list(self.components.keys())

        for entity in entities:
            entity_id = str(entity.get(id_field, "unknown"))
            values = {field: entity.get(field) for field in value_fields}
            metadata = {k: v for k, v in entity.items()
                       if k not in value_fields and k != id_field}

            try:
                result = self.score(values, entity_id=entity_id, metadata=metadata)
                results.append(result)
            except Exception as e:
                logger.error(f"Error scoring entity {entity_id}: {e}")
                continue

        return results

    def _determine_grade(self, score: float) -> str:
        """Determine letter grade from score."""
        for threshold, grade in sorted(self.grade_thresholds.items(), reverse=True):
            if score >= threshold:
                return grade
        return "F"

    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level from score."""
        for threshold, level in sorted(self.risk_thresholds.items(), reverse=True):
            if score >= threshold:
                return level
        return "Critical"

    def _generate_recommendations(
        self,
        component_scores: Dict[str, float],
        overall_score: float
    ) -> List[str]:
        """Generate recommendations based on scores."""
        recommendations = []

        for name, score in component_scores.items():
            if score < 50:
                component = self.components[name]
                recommendations.append(
                    f"Critical: Improve {name} (currently {score:.0f}/100) - {component.description}"
                )
            elif score < 70:
                component = self.components[name]
                recommendations.append(
                    f"Warning: Monitor {name} (currently {score:.0f}/100) - {component.description}"
                )

        for rule in self.recommendation_rules:
            condition = rule.get("condition")
            message = rule.get("message")

            if condition and message:
                try:
                    if condition(component_scores, overall_score):
                        recommendations.append(message)
                except Exception as e:
                    logger.warning(f"Error evaluating recommendation rule: {e}")

        return recommendations

    def get_component_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all scoring components."""
        return {
            name: {
                "weight": c.weight,
                "weight_percent": f"{c.weight * 100:.0f}%",
                "direction": c.direction.value,
                "range": f"{c.min_value} - {c.max_value}",
                "description": c.description
            }
            for name, c in self.components.items()
        }


class AggregatedScoringEngine:
    """
    Aggregates scores across multiple entities (e.g., department scores from subsidiaries).
    """

    def __init__(
        self,
        base_engine: WeightedScoringEngine,
        aggregation_method: str = "weighted_average"
    ):
        self.base_engine = base_engine
        self.aggregation_method = aggregation_method

    def aggregate(
        self,
        entities: List[Dict[str, Any]],
        group_id: str,
        weight_field: Optional[str] = None,
        id_field: str = "id"
    ) -> ScoreResult:
        """Aggregate scores across multiple entities."""
        if not entities:
            return ScoreResult(
                entity_id=group_id,
                overall_score=0.0,
                grade="F",
                component_scores={},
                component_details={},
                risk_level="Unknown",
                recommendations=["No data available for scoring"]
            )

        individual_scores = self.base_engine.score_batch(entities, id_field=id_field)

        if weight_field and self.aggregation_method == "weighted_average":
            weights = [e.get(weight_field, 1) for e in entities]
            total_weight = sum(weights)
            weights = [w / total_weight for w in weights]
        else:
            weights = [1 / len(entities)] * len(entities)

        if self.aggregation_method in ["weighted_average", "simple_average"]:
            overall_score = sum(
                score.overall_score * weight
                for score, weight in zip(individual_scores, weights)
            )
        elif self.aggregation_method == "min":
            overall_score = min(s.overall_score for s in individual_scores)
        elif self.aggregation_method == "max":
            overall_score = max(s.overall_score for s in individual_scores)
        else:
            overall_score = sum(s.overall_score for s in individual_scores) / len(individual_scores)

        component_scores = {}
        for name in self.base_engine.components.keys():
            if self.aggregation_method in ["weighted_average", "simple_average"]:
                component_scores[name] = sum(
                    s.component_scores.get(name, 0) * weight
                    for s, weight in zip(individual_scores, weights)
                )
            else:
                values = [s.component_scores.get(name, 0) for s in individual_scores]
                component_scores[name] = min(values) if self.aggregation_method == "min" else max(values)

        overall_score = round(overall_score, 2)

        return ScoreResult(
            entity_id=group_id,
            overall_score=overall_score,
            grade=self.base_engine._determine_grade(overall_score),
            component_scores=component_scores,
            component_details={
                "aggregation_method": self.aggregation_method,
                "entity_count": len(entities),
                "individual_scores": [
                    {"id": s.entity_id, "score": s.overall_score, "grade": s.grade}
                    for s in individual_scores
                ]
            },
            risk_level=self.base_engine._determine_risk_level(overall_score),
            metadata={"weight_field": weight_field}
        )


# =============================================================================
# Factory Functions for Cash Flow Intelligence
# =============================================================================

def create_financial_health_engine() -> WeightedScoringEngine:
    """Create a comprehensive SMB financial health scoring engine."""
    components = [
        ScoreComponent(
            name="current_ratio",
            weight=0.15,
            direction=ScoreDirection.HIGHER_IS_BETTER,
            min_value=0,
            max_value=3,
            description="Current assets / Current liabilities (target: 1.5-2.0)"
        ),
        ScoreComponent(
            name="quick_ratio",
            weight=0.15,
            direction=ScoreDirection.HIGHER_IS_BETTER,
            min_value=0,
            max_value=2,
            description="Liquid assets / Current liabilities (target: 1.0+)"
        ),
        ScoreComponent(
            name="gross_margin",
            weight=0.15,
            direction=ScoreDirection.HIGHER_IS_BETTER,
            min_value=0,
            max_value=100,
            description="Gross profit percentage"
        ),
        ScoreComponent(
            name="net_margin",
            weight=0.15,
            direction=ScoreDirection.HIGHER_IS_BETTER,
            min_value=-20,
            max_value=30,
            description="Net profit percentage"
        ),
        ScoreComponent(
            name="debt_to_equity",
            weight=0.10,
            direction=ScoreDirection.LOWER_IS_BETTER,
            min_value=0,
            max_value=4,
            description="Total debt / Equity (lower is safer)"
        ),
        ScoreComponent(
            name="revenue_growth",
            weight=0.15,
            direction=ScoreDirection.HIGHER_IS_BETTER,
            min_value=-20,
            max_value=50,
            description="Year-over-year revenue growth %"
        ),
        ScoreComponent(
            name="cash_conversion_cycle",
            weight=0.15,
            direction=ScoreDirection.LOWER_IS_BETTER,
            min_value=0,
            max_value=120,
            description="Days to convert investments to cash"
        ),
    ]

    return WeightedScoringEngine(components)


def create_smb_cash_flow_engine() -> WeightedScoringEngine:
    """Create a cash-flow focused scoring engine for SMBs."""
    components = [
        ScoreComponent(
            name="days_cash_on_hand",
            weight=0.25,
            direction=ScoreDirection.HIGHER_IS_BETTER,
            min_value=0,
            max_value=90,
            description="Days of operating expenses covered by cash"
        ),
        ScoreComponent(
            name="operating_cash_flow_ratio",
            weight=0.20,
            direction=ScoreDirection.HIGHER_IS_BETTER,
            min_value=0,
            max_value=2,
            description="Operating cash flow / Current liabilities"
        ),
        ScoreComponent(
            name="burn_rate_percent",
            weight=0.20,
            direction=ScoreDirection.LOWER_IS_BETTER,
            min_value=0,
            max_value=30,
            description="Monthly cash burn as % of reserves"
        ),
        ScoreComponent(
            name="days_sales_outstanding",
            weight=0.15,
            direction=ScoreDirection.LOWER_IS_BETTER,
            min_value=0,
            max_value=90,
            description="Average days to collect receivables"
        ),
        ScoreComponent(
            name="days_payables_outstanding",
            weight=0.10,
            direction=ScoreDirection.HIGHER_IS_BETTER,
            min_value=0,
            max_value=60,
            description="Average days to pay suppliers"
        ),
        ScoreComponent(
            name="free_cash_flow_margin",
            weight=0.10,
            direction=ScoreDirection.HIGHER_IS_BETTER,
            min_value=-20,
            max_value=30,
            description="Free cash flow as % of revenue"
        ),
    ]

    return WeightedScoringEngine(components)
