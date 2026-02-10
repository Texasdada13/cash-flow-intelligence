"""
Cash Flow Intelligence Assessment Questions

Comprehensive questionnaire organized by dimension:
1. Cash Visibility & Monitoring
2. Receivables Management
3. Payables Optimization
4. Working Capital Efficiency
5. Financial Planning & Forecasting

Each question has:
- ID and dimension assignment
- Question text and help text
- Answer options with scores (0-5 scale)
- Weight for importance within dimension
"""

from typing import Dict, List, Any

# Dimension definitions with weights
DIMENSIONS = {
    "cash_visibility": {
        "id": "cash_visibility",
        "name": "Cash Visibility & Monitoring",
        "description": "How well do you understand and track your current cash position?",
        "weight": 0.25,
        "icon": "bi-eye",
        "color": "#198754"
    },
    "receivables": {
        "id": "receivables",
        "name": "Receivables Management",
        "description": "How effectively do you manage customer payments and collections?",
        "weight": 0.20,
        "icon": "bi-arrow-down-circle",
        "color": "#20c997"
    },
    "payables": {
        "id": "payables",
        "name": "Payables Optimization",
        "description": "How strategically do you manage vendor payments and terms?",
        "weight": 0.15,
        "icon": "bi-arrow-up-circle",
        "color": "#0d6efd"
    },
    "working_capital": {
        "id": "working_capital",
        "name": "Working Capital Efficiency",
        "description": "How efficiently do you manage your operating cash cycle?",
        "weight": 0.20,
        "icon": "bi-arrow-repeat",
        "color": "#6f42c1"
    },
    "planning": {
        "id": "planning",
        "name": "Financial Planning & Forecasting",
        "description": "How well do you plan for and predict future cash needs?",
        "weight": 0.20,
        "icon": "bi-graph-up-arrow",
        "color": "#fd7e14"
    }
}

# Standard answer options for frequency questions
FREQUENCY_OPTIONS = [
    {"value": 0, "label": "Never", "description": "This is not done at all"},
    {"value": 1, "label": "Rarely", "description": "Done occasionally, not consistently"},
    {"value": 2, "label": "Sometimes", "description": "Done about half the time"},
    {"value": 3, "label": "Usually", "description": "Done most of the time"},
    {"value": 4, "label": "Almost Always", "description": "Done consistently with few exceptions"},
    {"value": 5, "label": "Always", "description": "Done every time without fail"}
]

# Standard answer options for agreement questions
AGREEMENT_OPTIONS = [
    {"value": 0, "label": "Strongly Disagree", "description": "Not at all accurate"},
    {"value": 1, "label": "Disagree", "description": "Mostly inaccurate"},
    {"value": 2, "label": "Somewhat Disagree", "description": "Slightly inaccurate"},
    {"value": 3, "label": "Somewhat Agree", "description": "Slightly accurate"},
    {"value": 4, "label": "Agree", "description": "Mostly accurate"},
    {"value": 5, "label": "Strongly Agree", "description": "Completely accurate"}
]

# Standard answer options for maturity questions
MATURITY_OPTIONS = [
    {"value": 0, "label": "Non-existent", "description": "No process or capability exists"},
    {"value": 1, "label": "Ad-hoc", "description": "Done informally without structure"},
    {"value": 2, "label": "Basic", "description": "Simple process in place"},
    {"value": 3, "label": "Defined", "description": "Documented and followed consistently"},
    {"value": 4, "label": "Managed", "description": "Measured and actively improved"},
    {"value": 5, "label": "Optimized", "description": "Best practices fully implemented"}
]

# Assessment questions organized by dimension
ASSESSMENT_QUESTIONS: List[Dict[str, Any]] = [
    # =========================================================================
    # DIMENSION 1: CASH VISIBILITY & MONITORING
    # =========================================================================
    {
        "id": "cv_01",
        "dimension": "cash_visibility",
        "question": "How often do you know your exact cash balance across all accounts?",
        "help_text": "Consider checking all bank accounts, credit lines, and cash equivalents.",
        "options": [
            {"value": 0, "label": "Monthly or less", "description": "Check once a month or rarely"},
            {"value": 1, "label": "Weekly", "description": "Check once a week"},
            {"value": 2, "label": "Several times a week", "description": "Check 2-3 times per week"},
            {"value": 3, "label": "Daily", "description": "Check once every day"},
            {"value": 4, "label": "Multiple times daily", "description": "Check several times each day"},
            {"value": 5, "label": "Real-time", "description": "Automated real-time visibility"}
        ],
        "weight": 1.2
    },
    {
        "id": "cv_02",
        "dimension": "cash_visibility",
        "question": "We have a single dashboard or report showing our consolidated cash position.",
        "help_text": "A unified view of cash across all accounts and entities.",
        "options": AGREEMENT_OPTIONS,
        "weight": 1.0
    },
    {
        "id": "cv_03",
        "dimension": "cash_visibility",
        "question": "We can see upcoming cash inflows and outflows for the next 2 weeks.",
        "help_text": "Visibility into scheduled receipts and payments.",
        "options": AGREEMENT_OPTIONS,
        "weight": 1.0
    },
    {
        "id": "cv_04",
        "dimension": "cash_visibility",
        "question": "Our cash position data is accurate and up-to-date.",
        "help_text": "No significant discrepancies between reported and actual cash.",
        "options": AGREEMENT_OPTIONS,
        "weight": 1.1
    },
    {
        "id": "cv_05",
        "dimension": "cash_visibility",
        "question": "We track cash by business unit, project, or cost center.",
        "help_text": "Ability to see cash allocation at a granular level.",
        "options": MATURITY_OPTIONS,
        "weight": 0.8
    },
    {
        "id": "cv_06",
        "dimension": "cash_visibility",
        "question": "We have alerts for low cash balances or unusual transactions.",
        "help_text": "Automated notifications for cash-related events.",
        "options": MATURITY_OPTIONS,
        "weight": 0.9
    },
    {
        "id": "cv_07",
        "dimension": "cash_visibility",
        "question": "We reconcile bank accounts promptly (within 2-3 days).",
        "help_text": "How quickly discrepancies are identified and resolved.",
        "options": FREQUENCY_OPTIONS,
        "weight": 0.9
    },
    {
        "id": "cv_08",
        "dimension": "cash_visibility",
        "question": "Management receives regular cash position reports.",
        "help_text": "Formal reporting to leadership on cash status.",
        "options": FREQUENCY_OPTIONS,
        "weight": 0.8
    },

    # =========================================================================
    # DIMENSION 2: RECEIVABLES MANAGEMENT
    # =========================================================================
    {
        "id": "ar_01",
        "dimension": "receivables",
        "question": "We have a formal credit policy for evaluating new customers.",
        "help_text": "Documented criteria for extending credit terms.",
        "options": MATURITY_OPTIONS,
        "weight": 1.0
    },
    {
        "id": "ar_02",
        "dimension": "receivables",
        "question": "We review customer credit limits regularly.",
        "help_text": "Periodic reassessment of customer creditworthiness.",
        "options": FREQUENCY_OPTIONS,
        "weight": 0.8
    },
    {
        "id": "ar_03",
        "dimension": "receivables",
        "question": "Invoices are sent within 24-48 hours of delivery/service completion.",
        "help_text": "Speed of invoice generation and delivery.",
        "options": FREQUENCY_OPTIONS,
        "weight": 1.1
    },
    {
        "id": "ar_04",
        "dimension": "receivables",
        "question": "We have a structured collections process with defined follow-up steps.",
        "help_text": "Documented escalation process for overdue accounts.",
        "options": MATURITY_OPTIONS,
        "weight": 1.2
    },
    {
        "id": "ar_05",
        "dimension": "receivables",
        "question": "We track Days Sales Outstanding (DSO) and act on trends.",
        "help_text": "Monitoring and managing the time to collect.",
        "options": MATURITY_OPTIONS,
        "weight": 1.0
    },
    {
        "id": "ar_06",
        "dimension": "receivables",
        "question": "We offer incentives for early payment (discounts, etc.).",
        "help_text": "Using payment terms to accelerate collections.",
        "options": MATURITY_OPTIONS,
        "weight": 0.7
    },
    {
        "id": "ar_07",
        "dimension": "receivables",
        "question": "We use electronic payment methods to speed collections.",
        "help_text": "ACH, credit cards, or other fast payment options.",
        "options": [
            {"value": 0, "label": "Checks only", "description": "Paper checks are primary payment method"},
            {"value": 1, "label": "Some electronic", "description": "Accept but don't encourage electronic"},
            {"value": 2, "label": "Prefer electronic", "description": "Encourage electronic payments"},
            {"value": 3, "label": "Mostly electronic", "description": "Most payments are electronic"},
            {"value": 4, "label": "Almost all electronic", "description": "Very few paper checks"},
            {"value": 5, "label": "All electronic", "description": "100% electronic payments"}
        ],
        "weight": 0.9
    },
    {
        "id": "ar_08",
        "dimension": "receivables",
        "question": "We have low bad debt write-offs (less than 1% of revenue).",
        "help_text": "Uncollectible accounts as a percentage of sales.",
        "options": AGREEMENT_OPTIONS,
        "weight": 1.0
    },

    # =========================================================================
    # DIMENSION 3: PAYABLES OPTIMIZATION
    # =========================================================================
    {
        "id": "ap_01",
        "dimension": "payables",
        "question": "We have negotiated favorable payment terms with key vendors.",
        "help_text": "Extended terms (Net 45, Net 60) or other favorable arrangements.",
        "options": MATURITY_OPTIONS,
        "weight": 1.1
    },
    {
        "id": "ap_02",
        "dimension": "payables",
        "question": "We strategically time vendor payments to optimize cash.",
        "help_text": "Paying on the due date rather than early, unless discounted.",
        "options": FREQUENCY_OPTIONS,
        "weight": 1.0
    },
    {
        "id": "ap_03",
        "dimension": "payables",
        "question": "We take advantage of early payment discounts when beneficial.",
        "help_text": "Evaluating ROI of early payment discounts.",
        "options": FREQUENCY_OPTIONS,
        "weight": 0.9
    },
    {
        "id": "ap_04",
        "dimension": "payables",
        "question": "We have a clear approval process for vendor payments.",
        "help_text": "Defined authorization levels and controls.",
        "options": MATURITY_OPTIONS,
        "weight": 0.8
    },
    {
        "id": "ap_05",
        "dimension": "payables",
        "question": "We track Days Payables Outstanding (DPO) and optimize timing.",
        "help_text": "Monitoring and managing payment cycles.",
        "options": MATURITY_OPTIONS,
        "weight": 1.0
    },
    {
        "id": "ap_06",
        "dimension": "payables",
        "question": "We batch payments to reduce processing costs and optimize cash flow.",
        "help_text": "Consolidating payments on set schedules.",
        "options": FREQUENCY_OPTIONS,
        "weight": 0.7
    },
    {
        "id": "ap_07",
        "dimension": "payables",
        "question": "We regularly review and renegotiate vendor contracts.",
        "help_text": "Periodic reassessment of vendor terms and pricing.",
        "options": FREQUENCY_OPTIONS,
        "weight": 0.8
    },
    {
        "id": "ap_08",
        "dimension": "payables",
        "question": "We maintain good vendor relationships while optimizing cash.",
        "help_text": "Balance between cash management and vendor partnerships.",
        "options": AGREEMENT_OPTIONS,
        "weight": 0.9
    },

    # =========================================================================
    # DIMENSION 4: WORKING CAPITAL EFFICIENCY
    # =========================================================================
    {
        "id": "wc_01",
        "dimension": "working_capital",
        "question": "We actively manage our cash conversion cycle.",
        "help_text": "Focused effort to reduce the time from cash out to cash in.",
        "options": MATURITY_OPTIONS,
        "weight": 1.2
    },
    {
        "id": "wc_02",
        "dimension": "working_capital",
        "question": "Our inventory levels are optimized to minimize cash tied up.",
        "help_text": "Balance between stock availability and cash investment.",
        "options": [
            {"value": 0, "label": "Not applicable", "description": "Service business, no inventory"},
            {"value": 1, "label": "Poor", "description": "Excess inventory, slow turns"},
            {"value": 2, "label": "Below average", "description": "Some excess, improving"},
            {"value": 3, "label": "Average", "description": "Industry-standard levels"},
            {"value": 4, "label": "Good", "description": "Well-managed, above average turns"},
            {"value": 5, "label": "Excellent", "description": "Just-in-time, minimal tied-up cash"}
        ],
        "weight": 0.9
    },
    {
        "id": "wc_03",
        "dimension": "working_capital",
        "question": "We have access to a line of credit or short-term financing.",
        "help_text": "Available credit facilities for working capital needs.",
        "options": [
            {"value": 0, "label": "No access", "description": "No credit facilities available"},
            {"value": 1, "label": "Difficult to obtain", "description": "Could get but challenging"},
            {"value": 2, "label": "Limited access", "description": "Small line available"},
            {"value": 3, "label": "Adequate access", "description": "Reasonable credit available"},
            {"value": 4, "label": "Good access", "description": "Comfortable credit facilities"},
            {"value": 5, "label": "Excellent access", "description": "Strong banking relationships, flexible terms"}
        ],
        "weight": 1.0
    },
    {
        "id": "wc_04",
        "dimension": "working_capital",
        "question": "We maintain an appropriate cash reserve for operations.",
        "help_text": "Buffer for unexpected expenses or slow periods.",
        "options": [
            {"value": 0, "label": "No reserve", "description": "Operating on thin margins"},
            {"value": 1, "label": "Less than 1 month", "description": "Minimal buffer"},
            {"value": 2, "label": "1-2 months", "description": "Some buffer in place"},
            {"value": 3, "label": "2-3 months", "description": "Reasonable reserve"},
            {"value": 4, "label": "3-6 months", "description": "Comfortable reserve"},
            {"value": 5, "label": "6+ months", "description": "Strong cash position"}
        ],
        "weight": 1.1
    },
    {
        "id": "wc_05",
        "dimension": "working_capital",
        "question": "We review and optimize our working capital metrics regularly.",
        "help_text": "Periodic analysis of current ratio, quick ratio, etc.",
        "options": FREQUENCY_OPTIONS,
        "weight": 0.8
    },
    {
        "id": "wc_06",
        "dimension": "working_capital",
        "question": "We have clear targets for key working capital ratios.",
        "help_text": "Defined goals for current ratio, DSO, DPO, etc.",
        "options": MATURITY_OPTIONS,
        "weight": 0.8
    },
    {
        "id": "wc_07",
        "dimension": "working_capital",
        "question": "We actively manage seasonal cash flow variations.",
        "help_text": "Planning for and smoothing seasonal cash patterns.",
        "options": MATURITY_OPTIONS,
        "weight": 0.9
    },
    {
        "id": "wc_08",
        "dimension": "working_capital",
        "question": "Excess cash is invested appropriately to earn returns.",
        "help_text": "Not leaving significant cash idle in low-interest accounts.",
        "options": MATURITY_OPTIONS,
        "weight": 0.7
    },

    # =========================================================================
    # DIMENSION 5: FINANCIAL PLANNING & FORECASTING
    # =========================================================================
    {
        "id": "fp_01",
        "dimension": "planning",
        "question": "We prepare regular cash flow forecasts.",
        "help_text": "Formal projections of future cash position.",
        "options": [
            {"value": 0, "label": "Never", "description": "No cash forecasting done"},
            {"value": 1, "label": "Annually", "description": "Once a year planning"},
            {"value": 2, "label": "Quarterly", "description": "Updated each quarter"},
            {"value": 3, "label": "Monthly", "description": "Monthly forecast updates"},
            {"value": 4, "label": "Weekly", "description": "Weekly rolling forecast"},
            {"value": 5, "label": "Continuous", "description": "Real-time rolling forecast"}
        ],
        "weight": 1.2
    },
    {
        "id": "fp_02",
        "dimension": "planning",
        "question": "Our cash forecasts are reasonably accurate (within 10%).",
        "help_text": "Historical accuracy of cash projections.",
        "options": AGREEMENT_OPTIONS,
        "weight": 1.0
    },
    {
        "id": "fp_03",
        "dimension": "planning",
        "question": "We run multiple scenarios (best case, worst case, expected).",
        "help_text": "Scenario planning for different outcomes.",
        "options": MATURITY_OPTIONS,
        "weight": 0.9
    },
    {
        "id": "fp_04",
        "dimension": "planning",
        "question": "We have identified our cash flow risks and have mitigation plans.",
        "help_text": "Understanding what could go wrong and being prepared.",
        "options": MATURITY_OPTIONS,
        "weight": 1.0
    },
    {
        "id": "fp_05",
        "dimension": "planning",
        "question": "Major expenditures and investments are carefully planned and timed.",
        "help_text": "Coordinating large cash outflows with available funds.",
        "options": FREQUENCY_OPTIONS,
        "weight": 0.9
    },
    {
        "id": "fp_06",
        "dimension": "planning",
        "question": "We have an emergency cash plan for unexpected situations.",
        "help_text": "Contingency plans for cash emergencies.",
        "options": MATURITY_OPTIONS,
        "weight": 1.0
    },
    {
        "id": "fp_07",
        "dimension": "planning",
        "question": "We integrate cash planning with overall business planning.",
        "help_text": "Cash considerations in strategic decisions.",
        "options": MATURITY_OPTIONS,
        "weight": 0.8
    },
    {
        "id": "fp_08",
        "dimension": "planning",
        "question": "We track actual vs. forecasted cash and analyze variances.",
        "help_text": "Learning from forecast accuracy to improve.",
        "options": FREQUENCY_OPTIONS,
        "weight": 0.9
    }
]


def get_questions_by_dimension(dimension_id: str) -> List[Dict]:
    """Get all questions for a specific dimension."""
    return [q for q in ASSESSMENT_QUESTIONS if q["dimension"] == dimension_id]


def get_dimension_info(dimension_id: str) -> Dict:
    """Get dimension metadata."""
    return DIMENSIONS.get(dimension_id, {})


def get_all_dimensions() -> List[Dict]:
    """Get all dimension info in order."""
    return list(DIMENSIONS.values())


def get_question_count() -> int:
    """Get total number of questions."""
    return len(ASSESSMENT_QUESTIONS)


def get_question_by_id(question_id: str) -> Dict:
    """Get a specific question by ID."""
    for q in ASSESSMENT_QUESTIONS:
        if q["id"] == question_id:
            return q
    return {}
