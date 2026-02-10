"""
Cash Flow Intelligence Assessment Module

Comprehensive cash flow health assessment with:
- Multi-dimensional questionnaire
- Weighted scoring engine
- Gap analysis and recommendations
"""

from .assessment_engine import AssessmentEngine, AssessmentResult
from .questions import ASSESSMENT_QUESTIONS, DIMENSIONS

__all__ = ['AssessmentEngine', 'AssessmentResult', 'ASSESSMENT_QUESTIONS', 'DIMENSIONS']
