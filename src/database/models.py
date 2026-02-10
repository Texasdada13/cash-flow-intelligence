"""
Database Models for Cash Flow Intelligence

SQLAlchemy models for companies, financial periods, cash flow entries,
forecasts, and chat sessions.
"""

import uuid
from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON

db = SQLAlchemy()


def generate_uuid():
    return str(uuid.uuid4())


class Company(db.Model):
    """
    Company/Business being analyzed.

    Represents an SMB whose cash flow we're tracking.
    """
    __tablename__ = 'companies'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(200), nullable=False)
    industry = db.Column(db.String(100))
    description = db.Column(db.Text)

    # Company details
    revenue_range = db.Column(db.String(50))  # e.g., "1M-5M", "5M-10M"
    employee_count = db.Column(db.Integer)
    founded_year = db.Column(db.Integer)
    fiscal_year_end = db.Column(db.String(10))  # e.g., "12-31"

    # Contact info
    contact_name = db.Column(db.String(200))
    contact_email = db.Column(db.String(200))

    # Financial health summary (calculated)
    health_score = db.Column(db.Float)
    risk_level = db.Column(db.String(20))
    cash_runway_months = db.Column(db.Float)
    last_analysis_date = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    periods = db.relationship('FinancialPeriod', backref='company', lazy='dynamic',
                             cascade='all, delete-orphan')
    forecasts = db.relationship('Forecast', backref='company', lazy='dynamic',
                               cascade='all, delete-orphan')
    chat_sessions = db.relationship('ChatSession', backref='company', lazy='dynamic',
                                   cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'industry': self.industry,
            'description': self.description,
            'revenue_range': self.revenue_range,
            'employee_count': self.employee_count,
            'founded_year': self.founded_year,
            'fiscal_year_end': self.fiscal_year_end,
            'contact_name': self.contact_name,
            'contact_email': self.contact_email,
            'health_score': self.health_score,
            'risk_level': self.risk_level,
            'cash_runway_months': self.cash_runway_months,
            'last_analysis_date': self.last_analysis_date.isoformat() if self.last_analysis_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FinancialPeriod(db.Model):
    """
    Financial period data (monthly/quarterly).

    Contains P&L and balance sheet data for a single period.
    """
    __tablename__ = 'financial_periods'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False)

    # Period identification
    period_type = db.Column(db.String(20), default='monthly')  # monthly, quarterly
    period_date = db.Column(db.Date, nullable=False)  # First day of period
    period_label = db.Column(db.String(20))  # e.g., "Jan 2024", "Q1 2024"

    # Income Statement Items
    revenue = db.Column(db.Float, default=0)
    cogs = db.Column(db.Float, default=0)  # Cost of goods sold
    gross_profit = db.Column(db.Float, default=0)
    operating_expenses = db.Column(db.Float, default=0)
    payroll = db.Column(db.Float, default=0)
    rent = db.Column(db.Float, default=0)
    utilities = db.Column(db.Float, default=0)
    marketing = db.Column(db.Float, default=0)
    other_expenses = db.Column(db.Float, default=0)
    operating_income = db.Column(db.Float, default=0)
    interest_expense = db.Column(db.Float, default=0)
    net_income = db.Column(db.Float, default=0)

    # Balance Sheet Items
    cash = db.Column(db.Float, default=0)
    accounts_receivable = db.Column(db.Float, default=0)
    inventory = db.Column(db.Float, default=0)
    other_current_assets = db.Column(db.Float, default=0)
    total_current_assets = db.Column(db.Float, default=0)
    fixed_assets = db.Column(db.Float, default=0)
    total_assets = db.Column(db.Float, default=0)

    accounts_payable = db.Column(db.Float, default=0)
    short_term_debt = db.Column(db.Float, default=0)
    accrued_expenses = db.Column(db.Float, default=0)
    total_current_liabilities = db.Column(db.Float, default=0)
    long_term_debt = db.Column(db.Float, default=0)
    total_liabilities = db.Column(db.Float, default=0)
    total_equity = db.Column(db.Float, default=0)

    # Calculated Metrics (stored for quick access)
    current_ratio = db.Column(db.Float)
    quick_ratio = db.Column(db.Float)
    gross_margin = db.Column(db.Float)
    net_margin = db.Column(db.Float)
    days_sales_outstanding = db.Column(db.Float)
    days_payables_outstanding = db.Column(db.Float)
    cash_conversion_cycle = db.Column(db.Float)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cash_flows = db.relationship('CashFlowEntry', backref='period', lazy='dynamic',
                                cascade='all, delete-orphan')

    def calculate_metrics(self):
        """Calculate and store financial metrics"""
        # Current ratio
        if self.total_current_liabilities > 0:
            self.current_ratio = self.total_current_assets / self.total_current_liabilities
        else:
            self.current_ratio = None

        # Quick ratio
        quick_assets = self.cash + self.accounts_receivable
        if self.total_current_liabilities > 0:
            self.quick_ratio = quick_assets / self.total_current_liabilities
        else:
            self.quick_ratio = None

        # Gross margin
        if self.revenue > 0:
            self.gross_margin = (self.gross_profit / self.revenue) * 100
        else:
            self.gross_margin = None

        # Net margin
        if self.revenue > 0:
            self.net_margin = (self.net_income / self.revenue) * 100
        else:
            self.net_margin = None

        # DSO (simplified - assumes 30 day month)
        if self.revenue > 0:
            daily_revenue = self.revenue / 30
            self.days_sales_outstanding = self.accounts_receivable / daily_revenue if daily_revenue > 0 else None
        else:
            self.days_sales_outstanding = None

        # DPO (simplified)
        daily_cogs = self.cogs / 30 if self.cogs > 0 else 1
        self.days_payables_outstanding = self.accounts_payable / daily_cogs if daily_cogs > 0 else None

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'period_type': self.period_type,
            'period_date': self.period_date.isoformat() if self.period_date else None,
            'period_label': self.period_label,
            # Income statement
            'revenue': self.revenue,
            'cogs': self.cogs,
            'gross_profit': self.gross_profit,
            'operating_expenses': self.operating_expenses,
            'payroll': self.payroll,
            'operating_income': self.operating_income,
            'net_income': self.net_income,
            # Balance sheet
            'cash': self.cash,
            'accounts_receivable': self.accounts_receivable,
            'inventory': self.inventory,
            'total_current_assets': self.total_current_assets,
            'accounts_payable': self.accounts_payable,
            'total_current_liabilities': self.total_current_liabilities,
            'total_equity': self.total_equity,
            # Metrics
            'current_ratio': self.current_ratio,
            'quick_ratio': self.quick_ratio,
            'gross_margin': self.gross_margin,
            'net_margin': self.net_margin,
            'days_sales_outstanding': self.days_sales_outstanding,
            'days_payables_outstanding': self.days_payables_outstanding,
            'cash_conversion_cycle': self.cash_conversion_cycle
        }


class CashFlowEntry(db.Model):
    """
    Detailed cash flow entry.

    Individual cash inflow/outflow transactions or summaries.
    """
    __tablename__ = 'cash_flow_entries'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    period_id = db.Column(db.String(36), db.ForeignKey('financial_periods.id'), nullable=False)

    # Entry details
    entry_date = db.Column(db.Date, nullable=False)
    entry_type = db.Column(db.String(20))  # inflow, outflow
    category = db.Column(db.String(100))  # operating, investing, financing
    subcategory = db.Column(db.String(100))  # collections, payroll, loan_payment, etc.
    description = db.Column(db.String(500))
    amount = db.Column(db.Float, nullable=False)

    # For recurring entries
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_pattern = db.Column(db.String(50))  # weekly, monthly, etc.

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'period_id': self.period_id,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'entry_type': self.entry_type,
            'category': self.category,
            'subcategory': self.subcategory,
            'description': self.description,
            'amount': self.amount,
            'is_recurring': self.is_recurring,
            'recurrence_pattern': self.recurrence_pattern
        }


class Forecast(db.Model):
    """
    Cash flow forecast results.

    Stores forecast outputs for reference and comparison.
    """
    __tablename__ = 'forecasts'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False)

    # Forecast metadata
    forecast_date = db.Column(db.DateTime, default=datetime.utcnow)
    scenario = db.Column(db.String(50))  # baseline, optimistic, pessimistic
    model_type = db.Column(db.String(50))  # prophet, statistical
    periods_forecast = db.Column(db.Integer)
    confidence_level = db.Column(db.Float)

    # Key outputs
    runway_months = db.Column(db.Float)
    zero_cash_date = db.Column(db.Date)
    ending_cash_predicted = db.Column(db.Float)

    # Full forecast data (JSON)
    forecast_data = db.Column(JSON)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'forecast_date': self.forecast_date.isoformat() if self.forecast_date else None,
            'scenario': self.scenario,
            'model_type': self.model_type,
            'periods_forecast': self.periods_forecast,
            'confidence_level': self.confidence_level,
            'runway_months': self.runway_months,
            'zero_cash_date': self.zero_cash_date.isoformat() if self.zero_cash_date else None,
            'ending_cash_predicted': self.ending_cash_predicted,
            'forecast_data': self.forecast_data
        }


class AssessmentResult(db.Model):
    """
    Assessment result storage.

    Persists completed assessments for history and comparison.
    """
    __tablename__ = 'assessment_results'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=True)

    # Assessment metadata
    assessment_date = db.Column(db.DateTime, default=datetime.utcnow)
    company_name = db.Column(db.String(200))  # For anonymous assessments
    industry = db.Column(db.String(100))

    # Scores
    overall_score = db.Column(db.Float)
    overall_grade = db.Column(db.String(2))
    risk_level = db.Column(db.String(20))

    # Dimension scores (JSON)
    dimension_scores = db.Column(JSON)

    # Raw answers (JSON)
    answers = db.Column(JSON)

    # Recommendations (JSON)
    recommendations = db.Column(JSON)

    # Strengths and gaps (JSON)
    strengths = db.Column(JSON)
    gaps = db.Column(JSON)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    company = db.relationship('Company', backref=db.backref('assessments', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'company_name': self.company_name,
            'industry': self.industry,
            'assessment_date': self.assessment_date.isoformat() if self.assessment_date else None,
            'overall_score': self.overall_score,
            'overall_grade': self.overall_grade,
            'risk_level': self.risk_level,
            'dimension_scores': self.dimension_scores,
            'recommendations': self.recommendations,
            'strengths': self.strengths,
            'gaps': self.gaps,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Framework(db.Model):
    """
    Generated framework storage.

    Persists frameworks generated by AI.
    """
    __tablename__ = 'frameworks'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=True)
    assessment_id = db.Column(db.String(36), db.ForeignKey('assessment_results.id'), nullable=True)

    # Framework metadata
    framework_type = db.Column(db.String(100))  # cash_management, credit_collections, working_capital, kpi_dashboard
    title = db.Column(db.String(300))
    description = db.Column(db.Text)

    # Generated content (JSON with sections)
    content = db.Column(JSON)

    # Context used for generation
    context = db.Column(JSON)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'assessment_id': self.assessment_id,
            'framework_type': self.framework_type,
            'title': self.title,
            'description': self.description,
            'content': self.content,
            'context': self.context,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Roadmap(db.Model):
    """
    Implementation roadmap storage.

    Persists action plans generated from assessments.
    """
    __tablename__ = 'roadmaps'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=True)
    assessment_id = db.Column(db.String(36), db.ForeignKey('assessment_results.id'), nullable=True)

    # Roadmap metadata
    title = db.Column(db.String(300))
    description = db.Column(db.Text)
    total_phases = db.Column(db.Integer)
    estimated_duration_months = db.Column(db.Integer)

    # Phases with actions (JSON)
    phases = db.Column(JSON)

    # Quick wins identified (JSON)
    quick_wins = db.Column(JSON)

    # Success metrics (JSON)
    success_metrics = db.Column(JSON)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'assessment_id': self.assessment_id,
            'title': self.title,
            'description': self.description,
            'total_phases': self.total_phases,
            'estimated_duration_months': self.estimated_duration_months,
            'phases': self.phases,
            'quick_wins': self.quick_wins,
            'success_metrics': self.success_metrics,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Document(db.Model):
    """
    Generated document storage.

    Persists reports and documents generated by AI.
    """
    __tablename__ = 'documents'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=True)
    assessment_id = db.Column(db.String(36), db.ForeignKey('assessment_results.id'), nullable=True)

    # Document metadata
    doc_type = db.Column(db.String(100))  # executive_summary, board_presentation, investor_update, etc.
    title = db.Column(db.String(300))
    format = db.Column(db.String(20), default='html')  # html, pdf, markdown

    # Generated content
    content = db.Column(db.Text)

    # Context used for generation
    context = db.Column(JSON)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'assessment_id': self.assessment_id,
            'doc_type': self.doc_type,
            'title': self.title,
            'format': self.format,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ChatSession(db.Model):
    """
    AI chat session storage.

    Persists conversation history for each company.
    """
    __tablename__ = 'chat_sessions'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False)

    # Session details
    mode = db.Column(db.String(50), default='general')
    message_count = db.Column(db.Integer, default=0)
    conversation_history = db.Column(JSON)

    # Context at time of session
    health_score_snapshot = db.Column(db.Float)
    cash_snapshot = db.Column(db.Float)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'mode': self.mode,
            'message_count': self.message_count,
            'health_score_snapshot': self.health_score_snapshot,
            'cash_snapshot': self.cash_snapshot,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None
        }

    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        if self.conversation_history is None:
            self.conversation_history = []

        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.message_count = len(self.conversation_history)
        self.last_activity = datetime.utcnow()
