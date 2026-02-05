"""
Patterns Module for Cash Flow Intelligence

Reusable analytical patterns adapted from Patriot Tech's universal business solution framework.
"""

from .risk_classification import (
    RiskClassifier,
    MultiDimensionalRiskClassifier,
    RiskLevel,
    RiskThreshold,
    RiskClassification,
    create_health_score_classifier,
    create_financial_risk_classifier,
    create_cash_flow_risk_classifier
)

from .weighted_scoring import (
    WeightedScoringEngine,
    AggregatedScoringEngine,
    ScoreComponent,
    ScoreDirection,
    ScoreResult,
    create_financial_health_engine,
    create_smb_cash_flow_engine
)

from .benchmark_engine import (
    BenchmarkEngine,
    KPIDefinition,
    KPIDirection,
    KPICategory,
    KPIScore,
    BenchmarkReport,
    create_smb_financial_benchmarks,
    create_cash_flow_benchmarks
)

__all__ = [
    # Risk Classification
    'RiskClassifier',
    'MultiDimensionalRiskClassifier',
    'RiskLevel',
    'RiskThreshold',
    'RiskClassification',
    'create_health_score_classifier',
    'create_financial_risk_classifier',
    'create_cash_flow_risk_classifier',
    # Weighted Scoring
    'WeightedScoringEngine',
    'AggregatedScoringEngine',
    'ScoreComponent',
    'ScoreDirection',
    'ScoreResult',
    'create_financial_health_engine',
    'create_smb_cash_flow_engine',
    # Benchmarking
    'BenchmarkEngine',
    'KPIDefinition',
    'KPIDirection',
    'KPICategory',
    'KPIScore',
    'BenchmarkReport',
    'create_smb_financial_benchmarks',
    'create_cash_flow_benchmarks',
]
