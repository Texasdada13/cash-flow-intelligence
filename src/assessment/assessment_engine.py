"""
Cash Flow Assessment Engine

Scores assessment responses and generates insights:
- Overall health score (0-100)
- Dimension scores
- Gap analysis
- Prioritized recommendations
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from .questions import (
    ASSESSMENT_QUESTIONS,
    DIMENSIONS,
    get_questions_by_dimension,
    get_dimension_info
)

logger = logging.getLogger(__name__)


@dataclass
class DimensionScore:
    """Score for a single assessment dimension"""
    dimension_id: str
    dimension_name: str
    raw_score: float  # Sum of weighted scores
    max_score: float  # Maximum possible score
    percentage: float  # 0-100 percentage
    grade: str  # A, B, C, D, F
    level: str  # excellent, good, fair, needs_improvement, critical
    answered_questions: int
    total_questions: int
    strengths: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)


@dataclass
class AssessmentResult:
    """Complete assessment result"""
    assessment_id: str
    completed_at: datetime
    overall_score: float  # 0-100
    overall_grade: str
    overall_level: str
    dimension_scores: Dict[str, DimensionScore]
    strengths: List[str]
    gaps: List[str]
    recommendations: List[Dict[str, Any]]
    risk_level: str  # low, medium, high, critical
    answers: Dict[str, int]  # question_id -> answer value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "assessment_id": self.assessment_id,
            "completed_at": self.completed_at.isoformat(),
            "overall_score": round(self.overall_score, 1),
            "overall_grade": self.overall_grade,
            "overall_level": self.overall_level,
            "risk_level": self.risk_level,
            "dimension_scores": {
                dim_id: {
                    "dimension_id": ds.dimension_id,
                    "dimension_name": ds.dimension_name,
                    "percentage": round(ds.percentage, 1),
                    "grade": ds.grade,
                    "level": ds.level,
                    "answered_questions": ds.answered_questions,
                    "total_questions": ds.total_questions,
                    "strengths": ds.strengths,
                    "gaps": ds.gaps
                }
                for dim_id, ds in self.dimension_scores.items()
            },
            "strengths": self.strengths,
            "gaps": self.gaps,
            "recommendations": self.recommendations,
            "answers": self.answers
        }


class AssessmentEngine:
    """
    Engine for scoring cash flow assessments.

    Calculates weighted scores across dimensions and generates
    actionable insights and recommendations.

    Example:
        engine = AssessmentEngine()

        answers = {
            "cv_01": 3,  # Daily cash visibility
            "cv_02": 4,  # Strong agreement on dashboard
            "ar_01": 2,  # Basic credit policy
            ...
        }

        result = engine.calculate_score(answers, assessment_id="abc123")
        print(f"Overall Score: {result.overall_score}")
        print(f"Grade: {result.overall_grade}")
    """

    # Grade thresholds
    GRADE_THRESHOLDS = {
        90: ("A", "excellent"),
        80: ("B", "good"),
        70: ("C", "fair"),
        60: ("D", "needs_improvement"),
        0: ("F", "critical")
    }

    # Recommendations by dimension and score level
    RECOMMENDATIONS = {
        "cash_visibility": {
            "critical": [
                {
                    "priority": "high",
                    "title": "Implement Daily Cash Tracking",
                    "description": "Set up a simple spreadsheet or tool to record daily cash balances across all accounts.",
                    "impact": "Prevent cash surprises and enable better planning",
                    "effort": "low",
                    "timeframe": "1 week"
                },
                {
                    "priority": "high",
                    "title": "Create Cash Position Dashboard",
                    "description": "Build a consolidated view of all cash accounts updated at least daily.",
                    "impact": "Real-time visibility into available cash",
                    "effort": "medium",
                    "timeframe": "2-4 weeks"
                }
            ],
            "needs_improvement": [
                {
                    "priority": "medium",
                    "title": "Automate Bank Reconciliation",
                    "description": "Connect accounting system to bank feeds for automatic reconciliation.",
                    "impact": "Reduce errors and save time on cash tracking",
                    "effort": "medium",
                    "timeframe": "2-4 weeks"
                }
            ],
            "fair": [
                {
                    "priority": "low",
                    "title": "Add Cash Alerts",
                    "description": "Set up automated alerts for low balances or unusual transactions.",
                    "impact": "Proactive identification of cash issues",
                    "effort": "low",
                    "timeframe": "1 week"
                }
            ]
        },
        "receivables": {
            "critical": [
                {
                    "priority": "high",
                    "title": "Establish Collection Process",
                    "description": "Create a formal, documented collections process with defined follow-up steps and escalation.",
                    "impact": "Faster collection of outstanding receivables",
                    "effort": "medium",
                    "timeframe": "2-4 weeks"
                },
                {
                    "priority": "high",
                    "title": "Invoice Immediately",
                    "description": "Send invoices within 24 hours of service delivery or product shipment.",
                    "impact": "Reduce DSO by 5-10 days",
                    "effort": "low",
                    "timeframe": "immediate"
                }
            ],
            "needs_improvement": [
                {
                    "priority": "medium",
                    "title": "Implement Credit Policy",
                    "description": "Create formal credit evaluation criteria for new customers.",
                    "impact": "Reduce bad debt and collection issues",
                    "effort": "medium",
                    "timeframe": "2-4 weeks"
                }
            ],
            "fair": [
                {
                    "priority": "medium",
                    "title": "Offer Electronic Payment Options",
                    "description": "Enable ACH, credit card, and online payment to speed collections.",
                    "impact": "Faster payments, reduced processing time",
                    "effort": "low",
                    "timeframe": "1-2 weeks"
                }
            ]
        },
        "payables": {
            "critical": [
                {
                    "priority": "high",
                    "title": "Negotiate Extended Terms",
                    "description": "Request Net 45 or Net 60 terms from major vendors.",
                    "impact": "Improve cash flow by extending payment cycles",
                    "effort": "low",
                    "timeframe": "1-2 weeks"
                }
            ],
            "needs_improvement": [
                {
                    "priority": "medium",
                    "title": "Optimize Payment Timing",
                    "description": "Pay on the due date, not before, unless taking an early payment discount.",
                    "impact": "Maximize cash availability",
                    "effort": "low",
                    "timeframe": "immediate"
                }
            ],
            "fair": [
                {
                    "priority": "low",
                    "title": "Evaluate Early Payment Discounts",
                    "description": "Calculate ROI on early payment discounts vs. keeping cash longer.",
                    "impact": "Optimize cash vs. discount trade-offs",
                    "effort": "low",
                    "timeframe": "1 week"
                }
            ]
        },
        "working_capital": {
            "critical": [
                {
                    "priority": "high",
                    "title": "Build Cash Reserve",
                    "description": "Target 2-3 months of operating expenses as a minimum cash buffer.",
                    "impact": "Survive unexpected disruptions",
                    "effort": "high",
                    "timeframe": "3-6 months"
                },
                {
                    "priority": "high",
                    "title": "Establish Credit Line",
                    "description": "Set up a business line of credit before you need it.",
                    "impact": "Access to emergency funds when needed",
                    "effort": "medium",
                    "timeframe": "4-8 weeks"
                }
            ],
            "needs_improvement": [
                {
                    "priority": "medium",
                    "title": "Reduce Cash Conversion Cycle",
                    "description": "Focus on reducing DSO and increasing DPO to free up cash.",
                    "impact": "Unlock cash trapped in working capital",
                    "effort": "medium",
                    "timeframe": "ongoing"
                }
            ],
            "fair": [
                {
                    "priority": "low",
                    "title": "Optimize Inventory Levels",
                    "description": "Review inventory to reduce excess stock and tied-up cash.",
                    "impact": "Free up cash from slow-moving inventory",
                    "effort": "medium",
                    "timeframe": "4-8 weeks"
                }
            ]
        },
        "planning": {
            "critical": [
                {
                    "priority": "high",
                    "title": "Start Cash Forecasting",
                    "description": "Create a simple 13-week cash forecast updated weekly.",
                    "impact": "See cash problems before they happen",
                    "effort": "medium",
                    "timeframe": "2 weeks"
                },
                {
                    "priority": "high",
                    "title": "Create Emergency Cash Plan",
                    "description": "Document steps to take if facing a cash crunch.",
                    "impact": "Faster response to cash emergencies",
                    "effort": "low",
                    "timeframe": "1 week"
                }
            ],
            "needs_improvement": [
                {
                    "priority": "medium",
                    "title": "Add Scenario Planning",
                    "description": "Create best-case and worst-case cash scenarios.",
                    "impact": "Better preparation for different outcomes",
                    "effort": "low",
                    "timeframe": "1-2 weeks"
                }
            ],
            "fair": [
                {
                    "priority": "medium",
                    "title": "Track Forecast Accuracy",
                    "description": "Compare actual cash to forecast and analyze variances.",
                    "impact": "Improve forecasting over time",
                    "effort": "low",
                    "timeframe": "ongoing"
                }
            ]
        }
    }

    def __init__(self):
        """Initialize the assessment engine"""
        self.questions = {q["id"]: q for q in ASSESSMENT_QUESTIONS}
        self.dimensions = DIMENSIONS

    def calculate_score(
        self,
        answers: Dict[str, int],
        assessment_id: Optional[str] = None
    ) -> AssessmentResult:
        """
        Calculate assessment score from answers.

        Args:
            answers: Dict mapping question_id to answer value (0-5)
            assessment_id: Optional ID for this assessment

        Returns:
            AssessmentResult with scores and recommendations
        """
        import uuid

        if assessment_id is None:
            assessment_id = str(uuid.uuid4())

        # Calculate dimension scores
        dimension_scores = {}
        for dim_id, dim_info in self.dimensions.items():
            dim_score = self._calculate_dimension_score(dim_id, answers)
            dimension_scores[dim_id] = dim_score

        # Calculate overall score (weighted by dimension weights)
        total_weight = sum(d["weight"] for d in self.dimensions.values())
        overall_score = sum(
            dimension_scores[dim_id].percentage * self.dimensions[dim_id]["weight"]
            for dim_id in self.dimensions
        ) / total_weight

        # Determine overall grade and level
        overall_grade, overall_level = self._get_grade(overall_score)

        # Determine risk level
        risk_level = self._determine_risk_level(overall_score, dimension_scores)

        # Compile strengths and gaps
        strengths = self._compile_strengths(dimension_scores)
        gaps = self._compile_gaps(dimension_scores)

        # Generate recommendations
        recommendations = self._generate_recommendations(dimension_scores)

        return AssessmentResult(
            assessment_id=assessment_id,
            completed_at=datetime.now(),
            overall_score=overall_score,
            overall_grade=overall_grade,
            overall_level=overall_level,
            dimension_scores=dimension_scores,
            strengths=strengths,
            gaps=gaps,
            recommendations=recommendations,
            risk_level=risk_level,
            answers=answers
        )

    def _calculate_dimension_score(
        self,
        dimension_id: str,
        answers: Dict[str, int]
    ) -> DimensionScore:
        """Calculate score for a single dimension"""
        questions = get_questions_by_dimension(dimension_id)
        dim_info = get_dimension_info(dimension_id)

        raw_score = 0
        max_score = 0
        answered = 0
        strengths = []
        gaps = []

        for question in questions:
            q_id = question["id"]
            weight = question.get("weight", 1.0)
            max_score += 5 * weight  # 5 is max answer value

            if q_id in answers:
                answer = answers[q_id]
                raw_score += answer * weight
                answered += 1

                # Identify strengths (score 4-5) and gaps (score 0-2)
                if answer >= 4:
                    strengths.append(question["question"])
                elif answer <= 2:
                    gaps.append(question["question"])

        # Calculate percentage
        percentage = (raw_score / max_score * 100) if max_score > 0 else 0

        # Get grade
        grade, level = self._get_grade(percentage)

        return DimensionScore(
            dimension_id=dimension_id,
            dimension_name=dim_info.get("name", dimension_id),
            raw_score=raw_score,
            max_score=max_score,
            percentage=percentage,
            grade=grade,
            level=level,
            answered_questions=answered,
            total_questions=len(questions),
            strengths=strengths[:3],  # Top 3
            gaps=gaps[:3]  # Top 3
        )

    def _get_grade(self, percentage: float) -> tuple:
        """Get grade and level for a percentage score"""
        for threshold, (grade, level) in sorted(
            self.GRADE_THRESHOLDS.items(), reverse=True
        ):
            if percentage >= threshold:
                return grade, level
        return "F", "critical"

    def _determine_risk_level(
        self,
        overall_score: float,
        dimension_scores: Dict[str, DimensionScore]
    ) -> str:
        """Determine overall risk level"""
        # Check for critical dimensions
        critical_dims = [
            ds for ds in dimension_scores.values()
            if ds.level == "critical"
        ]

        if len(critical_dims) >= 2 or overall_score < 40:
            return "critical"
        elif len(critical_dims) == 1 or overall_score < 55:
            return "high"
        elif overall_score < 70:
            return "medium"
        else:
            return "low"

    def _compile_strengths(
        self,
        dimension_scores: Dict[str, DimensionScore]
    ) -> List[str]:
        """Compile top strengths across all dimensions"""
        all_strengths = []
        for dim_id, ds in dimension_scores.items():
            dim_name = self.dimensions[dim_id]["name"]
            for strength in ds.strengths:
                all_strengths.append(f"{dim_name}: {strength}")

        return all_strengths[:5]  # Top 5 overall

    def _compile_gaps(
        self,
        dimension_scores: Dict[str, DimensionScore]
    ) -> List[str]:
        """Compile top gaps across all dimensions"""
        # Sort by dimension score (lowest first)
        sorted_dims = sorted(
            dimension_scores.items(),
            key=lambda x: x[1].percentage
        )

        all_gaps = []
        for dim_id, ds in sorted_dims:
            dim_name = self.dimensions[dim_id]["name"]
            for gap in ds.gaps:
                all_gaps.append(f"{dim_name}: {gap}")

        return all_gaps[:5]  # Top 5 priority gaps

    def _generate_recommendations(
        self,
        dimension_scores: Dict[str, DimensionScore]
    ) -> List[Dict[str, Any]]:
        """Generate prioritized recommendations based on scores"""
        recommendations = []

        # Sort dimensions by score (lowest first for priority)
        sorted_dims = sorted(
            dimension_scores.items(),
            key=lambda x: x[1].percentage
        )

        for dim_id, ds in sorted_dims:
            dim_recs = self.RECOMMENDATIONS.get(dim_id, {})

            # Get recommendations for this dimension's level
            level_recs = dim_recs.get(ds.level, [])

            for rec in level_recs:
                recommendations.append({
                    **rec,
                    "dimension": dim_id,
                    "dimension_name": ds.dimension_name
                })

            # Also include next level up recommendations for improvement
            if ds.level == "critical":
                for rec in dim_recs.get("needs_improvement", []):
                    recommendations.append({
                        **rec,
                        "dimension": dim_id,
                        "dimension_name": ds.dimension_name
                    })

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 99))

        return recommendations[:10]  # Top 10 recommendations

    def get_question(self, question_id: str) -> Dict:
        """Get a question by ID"""
        return self.questions.get(question_id, {})

    def get_all_questions(self) -> List[Dict]:
        """Get all questions"""
        return ASSESSMENT_QUESTIONS

    def get_questions_for_dimension(self, dimension_id: str) -> List[Dict]:
        """Get questions for a specific dimension"""
        return get_questions_by_dimension(dimension_id)

    def validate_answers(self, answers: Dict[str, int]) -> Dict[str, Any]:
        """
        Validate answer set.

        Returns dict with:
        - valid: bool
        - missing_questions: list of missing question IDs
        - invalid_values: list of questions with invalid values
        - completion_percentage: float
        """
        missing = []
        invalid = []

        for q_id in self.questions:
            if q_id not in answers:
                missing.append(q_id)
            elif not isinstance(answers[q_id], int) or answers[q_id] < 0 or answers[q_id] > 5:
                invalid.append(q_id)

        total = len(self.questions)
        answered = total - len(missing)

        return {
            "valid": len(missing) == 0 and len(invalid) == 0,
            "missing_questions": missing,
            "invalid_values": invalid,
            "completion_percentage": (answered / total * 100) if total > 0 else 0,
            "answered_count": answered,
            "total_count": total
        }


# Singleton instance
_engine: Optional[AssessmentEngine] = None


def get_assessment_engine() -> AssessmentEngine:
    """Get or create singleton assessment engine"""
    global _engine
    if _engine is None:
        _engine = AssessmentEngine()
    return _engine
