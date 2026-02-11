"""
Cash Flow Intelligence - Flask Web Application

AI-powered cash flow analysis and forecasting for SMBs.
Virtual CFO consulting through Claude AI.
"""

import os
import sys
import uuid
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_config
from src.database.models import db, Company, FinancialPeriod, CashFlowEntry, Forecast, ChatSession, AssessmentResult, Framework, Roadmap, Document
from src.ai_core.chat_engine import AIChatEngine, ConversationMode, get_chat_engine
from src.patterns.weighted_scoring import create_smb_cash_flow_engine
from src.patterns.benchmark_engine import create_cash_flow_benchmarks
from src.patterns.risk_classification import create_cash_flow_risk_classifier
from src.assessment import AssessmentEngine, ASSESSMENT_QUESTIONS, DIMENSIONS
from src.assessment.questions import get_questions_by_dimension
from src.integrations import IntegrationManager, IntegrationType, QuickBooksConfig, XeroConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# App Factory
# =============================================================================

def create_app(config_class=None):
    """Create Flask application"""
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["100 per minute"]
    )

    # Create tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created")

    # =============================================================================
    # Routes - Pages
    # =============================================================================

    @app.route('/')
    def index():
        """Landing page"""
        return render_template('index.html', app_name=app.config['APP_NAME'])

    @app.route('/dashboard')
    def dashboard():
        """Main dashboard"""
        companies = Company.query.order_by(Company.updated_at.desc()).all()
        return render_template('dashboard.html',
                             app_name=app.config['APP_NAME'],
                             companies=companies)

    @app.route('/company/<company_id>')
    def company_detail(company_id):
        """Company detail view"""
        company = Company.query.get_or_404(company_id)
        periods = FinancialPeriod.query.filter_by(company_id=company_id)\
                                       .order_by(FinancialPeriod.period_date.desc())\
                                       .limit(12).all()

        # Get latest forecast
        forecast = Forecast.query.filter_by(company_id=company_id)\
                                 .order_by(Forecast.created_at.desc())\
                                 .first()

        return render_template('company.html',
                             app_name=app.config['APP_NAME'],
                             company=company,
                             periods=periods,
                             forecast=forecast)

    @app.route('/chat')
    @app.route('/chat/<company_id>')
    def chat(company_id=None):
        """AI Chat interface"""
        company = None
        if company_id:
            company = Company.query.get(company_id)

        companies = Company.query.order_by(Company.name).all()

        return render_template('chat.html',
                             app_name=app.config['APP_NAME'],
                             company=company,
                             companies=companies)

    @app.route('/assessment')
    def assessment():
        """Cash Flow Health Assessment"""
        # Organize questions by dimension
        questions_by_dimension = {
            dim_id: get_questions_by_dimension(dim_id)
            for dim_id in DIMENSIONS.keys()
        }

        return render_template('assessment.html',
                             app_name=app.config['APP_NAME'],
                             dimensions=DIMENSIONS,
                             questions_by_dimension=questions_by_dimension,
                             total_questions=len(ASSESSMENT_QUESTIONS))

    @app.route('/frameworks')
    def frameworks():
        """Framework Generator page"""
        return render_template('frameworks.html',
                             app_name=app.config['APP_NAME'])

    @app.route('/reports')
    def reports():
        """Report Generator page"""
        assessments = AssessmentResult.query.order_by(AssessmentResult.created_at.desc()).limit(10).all()
        return render_template('reports.html',
                             app_name=app.config['APP_NAME'],
                             assessments=assessments)

    @app.route('/history')
    def history():
        """Assessment history page"""
        assessments = AssessmentResult.query.order_by(AssessmentResult.created_at.desc()).all()
        return render_template('history.html',
                             app_name=app.config['APP_NAME'],
                             assessments=assessments)

    @app.route('/assessment/<assessment_id>/results')
    def assessment_results(assessment_id):
        """View specific assessment results"""
        assessment = AssessmentResult.query.get_or_404(assessment_id)
        return render_template('assessment_results.html',
                             app_name=app.config['APP_NAME'],
                             assessment=assessment)

    @app.route('/roadmap/<roadmap_id>')
    def roadmap_view(roadmap_id):
        """View specific roadmap"""
        roadmap = Roadmap.query.get_or_404(roadmap_id)
        return render_template('roadmap.html',
                             app_name=app.config['APP_NAME'],
                             roadmap=roadmap)

    @app.route('/forecasts/<company_id>')
    def forecasts(company_id):
        """Forecast view"""
        company = Company.query.get_or_404(company_id)
        all_forecasts = Forecast.query.filter_by(company_id=company_id)\
                                      .order_by(Forecast.created_at.desc())\
                                      .limit(10).all()

        return render_template('forecasts.html',
                             app_name=app.config['APP_NAME'],
                             company=company,
                             forecasts=all_forecasts)

    @app.route('/benchmarks/<company_id>')
    def benchmarks(company_id):
        """Benchmark comparison view"""
        company = Company.query.get_or_404(company_id)
        return render_template('benchmarks.html',
                             app_name=app.config['APP_NAME'],
                             company=company)

    # =============================================================================
    # API Routes - Companies
    # =============================================================================

    @app.route('/api/companies', methods=['GET'])
    def api_list_companies():
        """List all companies"""
        companies = Company.query.order_by(Company.name).all()
        return jsonify({
            'companies': [c.to_dict() for c in companies]
        })

    @app.route('/api/companies', methods=['POST'])
    def api_create_company():
        """Create a new company"""
        data = request.json or {}

        company = Company(
            name=data.get('name', 'New Company'),
            industry=data.get('industry'),
            description=data.get('description'),
            revenue_range=data.get('revenue_range'),
            employee_count=data.get('employee_count'),
            contact_name=data.get('contact_name'),
            contact_email=data.get('contact_email')
        )

        db.session.add(company)
        db.session.commit()

        logger.info(f"Created company: {company.name}")
        return jsonify({
            'success': True,
            'company': company.to_dict()
        }), 201

    @app.route('/api/companies/<company_id>', methods=['GET'])
    def api_get_company(company_id):
        """Get company details"""
        company = Company.query.get_or_404(company_id)
        return jsonify(company.to_dict())

    @app.route('/api/companies/<company_id>', methods=['DELETE'])
    def api_delete_company(company_id):
        """Delete a company"""
        company = Company.query.get_or_404(company_id)
        db.session.delete(company)
        db.session.commit()

        return jsonify({'success': True})

    # =============================================================================
    # API Routes - Financial Data
    # =============================================================================

    @app.route('/api/companies/<company_id>/periods', methods=['GET'])
    def api_list_periods(company_id):
        """List financial periods for a company"""
        periods = FinancialPeriod.query.filter_by(company_id=company_id)\
                                       .order_by(FinancialPeriod.period_date.desc())\
                                       .all()
        return jsonify({
            'periods': [p.to_dict() for p in periods]
        })

    @app.route('/api/companies/<company_id>/periods', methods=['POST'])
    def api_create_period(company_id):
        """Create a financial period"""
        company = Company.query.get_or_404(company_id)
        data = request.json or {}

        period = FinancialPeriod(
            company_id=company_id,
            period_type=data.get('period_type', 'monthly'),
            period_date=datetime.strptime(data.get('period_date'), '%Y-%m-%d').date(),
            period_label=data.get('period_label'),
            revenue=data.get('revenue', 0),
            cogs=data.get('cogs', 0),
            gross_profit=data.get('gross_profit', 0),
            operating_expenses=data.get('operating_expenses', 0),
            payroll=data.get('payroll', 0),
            rent=data.get('rent', 0),
            net_income=data.get('net_income', 0),
            cash=data.get('cash', 0),
            accounts_receivable=data.get('accounts_receivable', 0),
            inventory=data.get('inventory', 0),
            total_current_assets=data.get('total_current_assets', 0),
            accounts_payable=data.get('accounts_payable', 0),
            total_current_liabilities=data.get('total_current_liabilities', 0),
            total_equity=data.get('total_equity', 0)
        )

        # Calculate metrics
        period.calculate_metrics()

        db.session.add(period)
        db.session.commit()

        # Update company summary
        _update_company_health(company)

        return jsonify({
            'success': True,
            'period': period.to_dict()
        }), 201

    def _update_company_health(company):
        """Update company health score based on latest data"""
        latest = FinancialPeriod.query.filter_by(company_id=company.id)\
                                      .order_by(FinancialPeriod.period_date.desc())\
                                      .first()

        if latest:
            # Use scoring engine
            engine = create_smb_cash_flow_engine()

            # Prepare metrics
            metrics = {
                'days_cash_on_hand': (latest.cash / (latest.operating_expenses / 30)) if latest.operating_expenses > 0 else 90,
                'operating_cash_flow_ratio': (latest.net_income + latest.operating_expenses * 0.1) / latest.total_current_liabilities if latest.total_current_liabilities > 0 else 1,
                'burn_rate_percent': 0 if latest.net_income >= 0 else abs(latest.net_income) / latest.cash * 100 if latest.cash > 0 else 30,
                'days_sales_outstanding': latest.days_sales_outstanding or 45,
                'days_payables_outstanding': latest.days_payables_outstanding or 30,
                'free_cash_flow_margin': (latest.net_income / latest.revenue * 100) if latest.revenue > 0 else 0
            }

            result = engine.score(metrics, entity_id=company.id)
            company.health_score = result.overall_score
            company.risk_level = result.risk_level

            # Calculate runway
            if latest.net_income < 0:
                monthly_burn = abs(latest.net_income)
                company.cash_runway_months = latest.cash / monthly_burn if monthly_burn > 0 else None
            else:
                company.cash_runway_months = None  # Not burning cash

            company.last_analysis_date = datetime.utcnow()
            db.session.commit()

    # =============================================================================
    # API Routes - Assessment
    # =============================================================================

    @app.route('/api/assessment/submit', methods=['POST'])
    def api_submit_assessment():
        """Submit assessment answers and get results"""
        data = request.json or {}
        answers = data.get('answers', {})
        company_id = data.get('company_id')
        company_name = data.get('company_name', 'Anonymous')
        industry = data.get('industry', 'General')

        if not answers:
            return jsonify({'success': False, 'error': 'No answers provided'}), 400

        # Create assessment engine and calculate score
        engine = AssessmentEngine()

        # Validate answers
        validation = engine.validate_answers(answers)
        if not validation['valid'] and validation['completion_percentage'] < 100:
            return jsonify({
                'success': False,
                'error': f"Assessment incomplete ({validation['answered_count']}/{validation['total_count']} questions answered)",
                'validation': validation
            }), 400

        # Calculate scores
        result = engine.calculate_score(answers)

        # Save to database
        assessment_record = AssessmentResult(
            id=result.assessment_id,
            company_id=company_id,
            company_name=company_name,
            industry=industry,
            overall_score=result.overall_score,
            overall_grade=result.overall_grade,
            risk_level=result.risk_level,
            dimension_scores={
                dim_id: {
                    'score': dim.score,
                    'percentage': dim.percentage,
                    'grade': dim.grade,
                    'name': dim.name
                }
                for dim_id, dim in result.dimension_scores.items()
            },
            answers=answers,
            recommendations=[rec.__dict__ if hasattr(rec, '__dict__') else rec for rec in result.recommendations],
            strengths=result.strengths,
            gaps=result.gaps
        )
        db.session.add(assessment_record)
        db.session.commit()

        logger.info(f"Assessment completed and saved: {result.assessment_id}, Score: {result.overall_score}")

        return jsonify({
            'success': True,
            'assessment': result.to_dict(),
            'assessment_id': assessment_record.id
        })

    @app.route('/api/assessment/questions', methods=['GET'])
    def api_get_assessment_questions():
        """Get all assessment questions"""
        return jsonify({
            'dimensions': DIMENSIONS,
            'questions': ASSESSMENT_QUESTIONS,
            'total_questions': len(ASSESSMENT_QUESTIONS)
        })

    @app.route('/api/assessment/questions/<dimension_id>', methods=['GET'])
    def api_get_dimension_questions(dimension_id):
        """Get questions for a specific dimension"""
        if dimension_id not in DIMENSIONS:
            return jsonify({'error': 'Invalid dimension'}), 404

        questions = get_questions_by_dimension(dimension_id)
        return jsonify({
            'dimension': DIMENSIONS[dimension_id],
            'questions': questions
        })

    # =============================================================================
    # API Routes - Assessment History
    # =============================================================================

    @app.route('/api/assessments', methods=['GET'])
    def api_list_assessments():
        """List all assessments"""
        assessments = AssessmentResult.query.order_by(AssessmentResult.created_at.desc()).all()
        return jsonify({
            'assessments': [a.to_dict() for a in assessments]
        })

    @app.route('/api/assessments/<assessment_id>', methods=['GET'])
    def api_get_assessment(assessment_id):
        """Get specific assessment"""
        assessment = AssessmentResult.query.get_or_404(assessment_id)
        return jsonify(assessment.to_dict())

    # =============================================================================
    # API Routes - Framework Generation
    # =============================================================================

    FRAMEWORK_TYPES = {
        'cash_management': {
            'title': 'Cash Management Policy',
            'description': 'Comprehensive policy for managing cash flows, reserves, and liquidity',
            'sections': ['Overview', 'Cash Reserve Requirements', 'Cash Flow Monitoring', 'Investment Guidelines', 'Emergency Protocols', 'Reporting Requirements']
        },
        'credit_collections': {
            'title': 'Credit & Collections Policy',
            'description': 'Guidelines for extending credit and collecting receivables',
            'sections': ['Credit Evaluation Criteria', 'Credit Limits', 'Payment Terms', 'Collection Process', 'Escalation Procedures', 'Write-off Policy']
        },
        'working_capital': {
            'title': 'Working Capital Strategy',
            'description': 'Strategic approach to optimizing working capital components',
            'sections': ['Current State Analysis', 'Target Metrics', 'Inventory Optimization', 'Receivables Management', 'Payables Strategy', 'Implementation Plan']
        },
        'kpi_dashboard': {
            'title': 'Cash Flow KPI Dashboard',
            'description': 'Key performance indicators for monitoring cash flow health',
            'sections': ['Executive Summary KPIs', 'Liquidity Metrics', 'Efficiency Metrics', 'Trend Indicators', 'Alert Thresholds', 'Reporting Cadence']
        }
    }

    @app.route('/api/frameworks/types', methods=['GET'])
    def api_framework_types():
        """Get available framework types"""
        return jsonify({'framework_types': FRAMEWORK_TYPES})

    @app.route('/api/frameworks/generate', methods=['POST'])
    @limiter.limit("5 per minute")
    def api_generate_framework():
        """Generate a framework using AI"""
        data = request.json or {}
        framework_type = data.get('framework_type')
        assessment_id = data.get('assessment_id')
        company_id = data.get('company_id')

        if framework_type not in FRAMEWORK_TYPES:
            return jsonify({'error': 'Invalid framework type'}), 400

        # Get assessment context if provided
        assessment = None
        if assessment_id:
            assessment = AssessmentResult.query.get(assessment_id)

        # Build context for AI
        context = {
            'framework_type': framework_type,
            'framework_info': FRAMEWORK_TYPES[framework_type],
            'assessment_score': assessment.overall_score if assessment else None,
            'assessment_grade': assessment.overall_grade if assessment else None,
            'dimension_scores': assessment.dimension_scores if assessment else None,
            'gaps': assessment.gaps if assessment else None,
            'industry': assessment.industry if assessment else data.get('industry', 'General')
        }

        # Generate framework using Claude
        try:
            engine = get_chat_engine()
            prompt = f"""Generate a comprehensive {FRAMEWORK_TYPES[framework_type]['title']} for a company in the {context['industry']} industry.

Assessment Context:
- Overall Score: {context['assessment_score'] or 'Not assessed'}
- Grade: {context['assessment_grade'] or 'N/A'}
- Key Gaps: {context['gaps'] or 'None identified'}

Generate detailed content for each section:
{chr(10).join(f'- {section}' for section in FRAMEWORK_TYPES[framework_type]['sections'])}

Format the response as a JSON object with each section as a key containing:
- 'content': The detailed content for that section
- 'recommendations': Specific actionable recommendations
- 'metrics': Any relevant metrics or KPIs

Be specific and actionable. Tailor recommendations to the assessment results."""

            # Use chat engine for generation
            temp_session = engine.create_session(
                company_name=assessment.company_name if assessment else 'Framework Generation',
                industry=context['industry'],
                financial_summary=None,
                mode=ConversationMode.GENERAL
            )

            response = engine.chat(temp_session.session_id, prompt)
            generated_content = response.get('message', '')

            # Parse response (attempt to extract JSON, fallback to raw content)
            import json as json_module
            try:
                content_start = generated_content.find('{')
                content_end = generated_content.rfind('}') + 1
                if content_start >= 0 and content_end > content_start:
                    framework_content = json_module.loads(generated_content[content_start:content_end])
                else:
                    framework_content = {'raw_content': generated_content}
            except json_module.JSONDecodeError:
                framework_content = {'raw_content': generated_content}

            # Save framework
            framework = Framework(
                company_id=company_id,
                assessment_id=assessment_id,
                framework_type=framework_type,
                title=FRAMEWORK_TYPES[framework_type]['title'],
                description=FRAMEWORK_TYPES[framework_type]['description'],
                content=framework_content,
                context=context
            )
            db.session.add(framework)
            db.session.commit()

            return jsonify({
                'success': True,
                'framework': framework.to_dict()
            })

        except Exception as e:
            logger.error(f"Framework generation error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/frameworks', methods=['GET'])
    def api_list_frameworks():
        """List generated frameworks"""
        frameworks = Framework.query.order_by(Framework.created_at.desc()).limit(20).all()
        return jsonify({
            'frameworks': [f.to_dict() for f in frameworks]
        })

    # =============================================================================
    # API Routes - Roadmap Generation
    # =============================================================================

    @app.route('/api/roadmaps/generate', methods=['POST'])
    @limiter.limit("5 per minute")
    def api_generate_roadmap():
        """Generate implementation roadmap from assessment"""
        data = request.json or {}
        assessment_id = data.get('assessment_id')
        company_id = data.get('company_id')
        duration_months = data.get('duration_months', 12)

        if not assessment_id:
            return jsonify({'error': 'assessment_id required'}), 400

        assessment = AssessmentResult.query.get_or_404(assessment_id)

        # Build roadmap from assessment recommendations
        try:
            engine = get_chat_engine()
            prompt = f"""Create a detailed implementation roadmap for improving cash flow management.

Assessment Results:
- Company: {assessment.company_name}
- Industry: {assessment.industry}
- Overall Score: {assessment.overall_score}/100 ({assessment.overall_grade})
- Risk Level: {assessment.risk_level}

Dimension Scores:
{chr(10).join(f"- {dim['name']}: {dim['score']}/100 ({dim['grade']})" for dim in (assessment.dimension_scores or {}).values())}

Key Gaps Identified:
{chr(10).join(f"- {gap}" for gap in (assessment.gaps or []))}

Create a {duration_months}-month implementation roadmap with:
1. 3-4 phases (Foundation, Quick Wins, Optimization, Excellence)
2. Specific actions for each phase with:
   - Action title
   - Description
   - Estimated effort (days)
   - Expected impact (high/medium/low)
   - Dependencies
3. Quick wins that can be achieved in first 30 days
4. Success metrics to track progress

Format as JSON with structure:
{{
  "phases": [
    {{
      "name": "Phase Name",
      "duration_weeks": X,
      "focus": "Main focus area",
      "actions": [
        {{"title": "", "description": "", "effort_days": X, "impact": "", "dependencies": []}}
      ]
    }}
  ],
  "quick_wins": [
    {{"title": "", "description": "", "expected_impact": ""}}
  ],
  "success_metrics": [
    {{"metric": "", "current": "", "target": "", "timeframe": ""}}
  ]
}}"""

            temp_session = engine.create_session(
                company_name=assessment.company_name,
                industry=assessment.industry,
                financial_summary=None,
                mode=ConversationMode.GENERAL
            )

            response = engine.chat(temp_session.session_id, prompt)
            generated_content = response.get('message', '')

            # Parse response
            import json as json_module
            try:
                content_start = generated_content.find('{')
                content_end = generated_content.rfind('}') + 1
                if content_start >= 0 and content_end > content_start:
                    roadmap_content = json_module.loads(generated_content[content_start:content_end])
                else:
                    roadmap_content = {'raw_content': generated_content}
            except json_module.JSONDecodeError:
                roadmap_content = {'raw_content': generated_content}

            # Save roadmap
            roadmap = Roadmap(
                company_id=company_id,
                assessment_id=assessment_id,
                title=f"Cash Flow Improvement Roadmap - {assessment.company_name}",
                description=f"Implementation roadmap based on assessment score of {assessment.overall_score}",
                total_phases=len(roadmap_content.get('phases', [])),
                estimated_duration_months=duration_months,
                phases=roadmap_content.get('phases', []),
                quick_wins=roadmap_content.get('quick_wins', []),
                success_metrics=roadmap_content.get('success_metrics', [])
            )
            db.session.add(roadmap)
            db.session.commit()

            return jsonify({
                'success': True,
                'roadmap': roadmap.to_dict()
            })

        except Exception as e:
            logger.error(f"Roadmap generation error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/roadmaps', methods=['GET'])
    def api_list_roadmaps():
        """List generated roadmaps"""
        roadmaps = Roadmap.query.order_by(Roadmap.created_at.desc()).limit(20).all()
        return jsonify({
            'roadmaps': [r.to_dict() for r in roadmaps]
        })

    # =============================================================================
    # API Routes - Document Generation
    # =============================================================================

    DOCUMENT_TYPES = {
        'executive_summary': {
            'title': 'Executive Summary',
            'description': 'High-level overview for C-suite executives'
        },
        'board_presentation': {
            'title': 'Board Presentation',
            'description': 'Detailed presentation for board meetings'
        },
        'investor_update': {
            'title': 'Investor Update',
            'description': 'Financial update for investors and stakeholders'
        },
        'lender_package': {
            'title': 'Lender Package',
            'description': 'Documentation package for lenders and creditors'
        },
        'detailed_analysis': {
            'title': 'Detailed Analysis Report',
            'description': 'Comprehensive analysis with recommendations'
        },
        'team_report': {
            'title': 'Team Report',
            'description': 'Operational report for finance team'
        }
    }

    @app.route('/api/documents/types', methods=['GET'])
    def api_document_types():
        """Get available document types"""
        return jsonify({'document_types': DOCUMENT_TYPES})

    @app.route('/api/documents/generate', methods=['POST'])
    @limiter.limit("5 per minute")
    def api_generate_document():
        """Generate a document using AI"""
        data = request.json or {}
        doc_type = data.get('doc_type')
        assessment_id = data.get('assessment_id')
        company_id = data.get('company_id')
        format_type = data.get('format', 'html')

        if doc_type not in DOCUMENT_TYPES:
            return jsonify({'error': 'Invalid document type'}), 400

        # Get assessment context if provided
        assessment = None
        if assessment_id:
            assessment = AssessmentResult.query.get(assessment_id)

        try:
            engine = get_chat_engine()

            doc_info = DOCUMENT_TYPES[doc_type]
            prompt = f"""Generate a professional {doc_info['title']} document.

Purpose: {doc_info['description']}

{"Assessment Context:" if assessment else ""}
{f"- Company: {assessment.company_name}" if assessment else ""}
{f"- Industry: {assessment.industry}" if assessment else ""}
{f"- Overall Score: {assessment.overall_score}/100 ({assessment.overall_grade})" if assessment else ""}
{f"- Risk Level: {assessment.risk_level}" if assessment else ""}

Generate a complete, professional document in {'HTML' if format_type == 'html' else 'Markdown'} format.
Include:
1. Executive summary
2. Key findings and metrics
3. Risk assessment
4. Recommendations
5. Next steps

Make it professional, concise, and actionable. Use appropriate formatting for the target audience."""

            temp_session = engine.create_session(
                company_name=assessment.company_name if assessment else 'Document Generation',
                industry=assessment.industry if assessment else 'General',
                financial_summary=None,
                mode=ConversationMode.GENERAL
            )

            response = engine.chat(temp_session.session_id, prompt)
            generated_content = response.get('message', '')

            # Save document
            document = Document(
                company_id=company_id,
                assessment_id=assessment_id,
                doc_type=doc_type,
                title=f"{doc_info['title']} - {assessment.company_name if assessment else 'Report'}",
                format=format_type,
                content=generated_content,
                context={
                    'assessment_id': assessment_id,
                    'assessment_score': assessment.overall_score if assessment else None
                }
            )
            db.session.add(document)
            db.session.commit()

            return jsonify({
                'success': True,
                'document': document.to_dict()
            })

        except Exception as e:
            logger.error(f"Document generation error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/documents', methods=['GET'])
    def api_list_documents():
        """List generated documents"""
        documents = Document.query.order_by(Document.created_at.desc()).limit(20).all()
        return jsonify({
            'documents': [d.to_dict() for d in documents]
        })

    @app.route('/api/documents/<document_id>', methods=['GET'])
    def api_get_document(document_id):
        """Get specific document"""
        document = Document.query.get_or_404(document_id)
        return jsonify(document.to_dict())

    # =============================================================================
    # API Routes - Chat
    # =============================================================================

    @app.route('/api/chat/session', methods=['POST'])
    def api_create_chat_session():
        """Create a new chat session"""
        data = request.json or {}
        company_id = data.get('company_id')

        company = Company.query.get(company_id) if company_id else None

        # Build financial context if company exists
        financial_summary = None
        if company:
            latest = FinancialPeriod.query.filter_by(company_id=company_id)\
                                          .order_by(FinancialPeriod.period_date.desc())\
                                          .first()
            if latest:
                financial_summary = {
                    'health_score': company.health_score,
                    'risk_level': company.risk_level,
                    'cash_runway_months': company.cash_runway_months,
                    'current_cash': latest.cash,
                    'monthly_burn': abs(latest.net_income) if latest.net_income < 0 else 0,
                    'dso': latest.days_sales_outstanding,
                    'dpo': latest.days_payables_outstanding,
                    'key_metrics': {
                        'current_ratio': latest.current_ratio,
                        'quick_ratio': latest.quick_ratio,
                        'gross_margin': latest.gross_margin,
                        'net_margin': latest.net_margin
                    }
                }

        # Create chat session
        engine = get_chat_engine()
        chat_session = engine.create_session(
            company_name=company.name if company else 'General Inquiry',
            industry=company.industry if company else 'general',
            financial_summary=financial_summary,
            mode=ConversationMode.GENERAL
        )

        # Store in database
        db_session = ChatSession(
            id=chat_session.session_id,
            company_id=company_id,
            mode='general',
            health_score_snapshot=company.health_score if company else None,
            cash_snapshot=financial_summary.get('current_cash') if financial_summary else None
        )
        db.session.add(db_session)
        db.session.commit()

        return jsonify({
            'session_id': chat_session.session_id,
            'company_name': chat_session.company_name,
            'suggested_prompts': engine.get_suggested_prompts(chat_session.session_id)
        })

    @app.route('/api/chat/message', methods=['POST'])
    def api_chat_message():
        """Send a chat message"""
        data = request.json or {}
        session_id = data.get('session_id')
        message = data.get('message', '')

        if not session_id or not message:
            return jsonify({'error': 'session_id and message required'}), 400

        engine = get_chat_engine()
        response = engine.chat(session_id, message)

        # Update database session
        db_session = ChatSession.query.get(session_id)
        if db_session:
            db_session.add_message('user', message)
            db_session.add_message('assistant', response.get('message', ''))
            db.session.commit()

        return jsonify(response)

    @app.route('/api/chat/stream', methods=['POST'])
    def api_chat_stream():
        """Stream chat response"""
        from flask import Response, stream_with_context
        import json

        data = request.json or {}
        session_id = data.get('session_id')
        message = data.get('message', '')

        if not session_id or not message:
            return jsonify({'error': 'session_id and message required'}), 400

        engine = get_chat_engine()

        def generate():
            full_response = ""
            for chunk in engine.stream_chat(session_id, message):
                if chunk['type'] == 'token':
                    full_response += chunk['content']
                yield f"data: {json.dumps(chunk)}\n\n"

            # Save to database
            db_session = ChatSession.query.get(session_id)
            if db_session:
                db_session.add_message('user', message)
                db_session.add_message('assistant', full_response)
                db.session.commit()

        return Response(
            stream_with_context(generate()),
            content_type='text/event-stream'
        )

    # =============================================================================
    # API Routes - Forecasting
    # =============================================================================

    @app.route('/api/companies/<company_id>/forecast', methods=['POST'])
    def api_generate_forecast(company_id):
        """Generate cash flow forecast"""
        from src.forecasting.cash_flow_forecaster import CashFlowForecaster, CashFlowData, ForecastScenario

        company = Company.query.get_or_404(company_id)
        data = request.json or {}

        periods_to_forecast = data.get('periods', 6)
        scenario = data.get('scenario', 'baseline')

        # Get historical data
        periods = FinancialPeriod.query.filter_by(company_id=company_id)\
                                       .order_by(FinancialPeriod.period_date.asc())\
                                       .all()

        if len(periods) < 3:
            return jsonify({
                'error': 'Need at least 3 periods of data for forecasting'
            }), 400

        # Prepare data for forecaster
        cash_data = CashFlowData(
            dates=[p.period_date for p in periods],
            cash_inflows=[p.revenue for p in periods],
            cash_outflows=[p.operating_expenses + p.cogs for p in periods],
            cash_balances=[p.cash for p in periods]
        )

        # Generate forecast
        forecaster = CashFlowForecaster()
        scenario_enum = ForecastScenario(scenario)
        result = forecaster.forecast(cash_data, periods_to_forecast, scenario_enum)

        # Save forecast
        forecast = Forecast(
            company_id=company_id,
            scenario=scenario,
            model_type=result.model_type,
            periods_forecast=periods_to_forecast,
            confidence_level=result.confidence_level,
            runway_months=result.runway_months,
            zero_cash_date=result.zero_cash_date,
            ending_cash_predicted=result.predicted_cash[-1] if result.predicted_cash else None,
            forecast_data=result.to_dict()
        )
        db.session.add(forecast)
        db.session.commit()

        return jsonify({
            'success': True,
            'forecast': result.to_dict()
        })

    # =============================================================================
    # API Routes - Benchmarks
    # =============================================================================

    @app.route('/api/companies/<company_id>/benchmark', methods=['GET'])
    def api_get_benchmark(company_id):
        """Get benchmark comparison"""
        company = Company.query.get_or_404(company_id)

        latest = FinancialPeriod.query.filter_by(company_id=company_id)\
                                      .order_by(FinancialPeriod.period_date.desc())\
                                      .first()

        if not latest:
            return jsonify({'error': 'No financial data available'}), 400

        # Create benchmark engine
        engine = create_cash_flow_benchmarks()

        # Prepare metrics
        metrics = {
            'days_cash_on_hand': (latest.cash / (latest.operating_expenses / 30)) if latest.operating_expenses > 0 else 45,
            'dso': latest.days_sales_outstanding or 45,
            'dpo': latest.days_payables_outstanding or 30,
            'cash_flow_margin': (latest.net_income / latest.revenue * 100) if latest.revenue > 0 else 0,
        }

        # Run benchmark
        report = engine.analyze(metrics, entity_id=company_id)

        return jsonify({
            'benchmark': report.to_dict()
        })

    # =============================================================================
    # API Routes - Integrations (QuickBooks/Xero)
    # =============================================================================

    # Integration manager instance
    _integration_manager = None

    def get_integration_manager(demo_mode: bool = False) -> IntegrationManager:
        """Get or create integration manager singleton"""
        nonlocal _integration_manager
        if _integration_manager is None:
            _integration_manager = IntegrationManager()
            if demo_mode or app.config.get('DEMO_MODE'):
                _integration_manager.enable_demo_mode()
            else:
                # Configure from environment
                if os.getenv('QUICKBOOKS_CLIENT_ID'):
                    _integration_manager.configure_quickbooks()
                if os.getenv('XERO_CLIENT_ID'):
                    _integration_manager.configure_xero()
        return _integration_manager

    @app.route('/integrations')
    def integrations_page():
        """Integrations management page"""
        manager = get_integration_manager()
        statuses = manager.get_all_statuses()
        return render_template('integrations.html',
                             app_name=app.config['APP_NAME'],
                             integrations=statuses)

    @app.route('/api/integrations/status', methods=['GET'])
    def api_integration_status():
        """Get status of all integrations"""
        manager = get_integration_manager()
        statuses = manager.get_all_statuses()
        return jsonify({
            'integrations': [
                {
                    'type': s.integration_type.value,
                    'is_connected': s.is_connected,
                    'last_sync': s.last_sync.isoformat() if s.last_sync else None,
                    'company_name': s.company_name,
                    'error': s.error_message
                }
                for s in statuses
            ]
        })

    @app.route('/api/integrations/demo/enable', methods=['POST'])
    def api_enable_demo_integration():
        """Enable demo mode for integrations"""
        manager = get_integration_manager(demo_mode=True)
        manager.enable_demo_mode()
        return jsonify({'success': True, 'message': 'Demo mode enabled'})

    # QuickBooks OAuth Flow
    @app.route('/api/integrations/quickbooks/auth-url', methods=['GET'])
    def api_quickbooks_auth_url():
        """Get QuickBooks OAuth authorization URL"""
        manager = get_integration_manager()
        state = str(uuid.uuid4())
        session['quickbooks_oauth_state'] = state
        auth_url = manager.get_auth_url(IntegrationType.QUICKBOOKS, state)
        return jsonify({'auth_url': auth_url, 'state': state})

    @app.route('/integrations/quickbooks/callback')
    def quickbooks_oauth_callback():
        """Handle QuickBooks OAuth callback"""
        code = request.args.get('code')
        realm_id = request.args.get('realmId')
        state = request.args.get('state')

        # Verify state
        stored_state = session.get('quickbooks_oauth_state')
        if state != stored_state:
            return render_template('integration_error.html',
                                 error='Invalid OAuth state',
                                 app_name=app.config['APP_NAME'])

        if not code or not realm_id:
            return render_template('integration_error.html',
                                 error='Missing authorization code or realm ID',
                                 app_name=app.config['APP_NAME'])

        manager = get_integration_manager()
        success = manager.handle_oauth_callback(IntegrationType.QUICKBOOKS, code, realm_id)

        if success:
            return redirect(url_for('integrations_page') + '?connected=quickbooks')
        else:
            return render_template('integration_error.html',
                                 error='Failed to connect to QuickBooks',
                                 app_name=app.config['APP_NAME'])

    @app.route('/api/integrations/quickbooks/disconnect', methods=['POST'])
    def api_disconnect_quickbooks():
        """Disconnect QuickBooks integration"""
        manager = get_integration_manager()
        manager.disconnect(IntegrationType.QUICKBOOKS)
        return jsonify({'success': True})

    # Xero OAuth Flow
    @app.route('/api/integrations/xero/auth-url', methods=['GET'])
    def api_xero_auth_url():
        """Get Xero OAuth authorization URL"""
        manager = get_integration_manager()
        state = str(uuid.uuid4())
        session['xero_oauth_state'] = state
        auth_url = manager.get_auth_url(IntegrationType.XERO, state)
        return jsonify({'auth_url': auth_url, 'state': state})

    @app.route('/integrations/xero/callback')
    def xero_oauth_callback():
        """Handle Xero OAuth callback"""
        code = request.args.get('code')
        state = request.args.get('state')

        # Verify state
        stored_state = session.get('xero_oauth_state')
        if state != stored_state:
            return render_template('integration_error.html',
                                 error='Invalid OAuth state',
                                 app_name=app.config['APP_NAME'])

        if not code:
            return render_template('integration_error.html',
                                 error='Missing authorization code',
                                 app_name=app.config['APP_NAME'])

        manager = get_integration_manager()
        success = manager.handle_oauth_callback(IntegrationType.XERO, code)

        if success:
            return redirect(url_for('integrations_page') + '?connected=xero')
        else:
            return render_template('integration_error.html',
                                 error='Failed to connect to Xero',
                                 app_name=app.config['APP_NAME'])

    @app.route('/api/integrations/xero/disconnect', methods=['POST'])
    def api_disconnect_xero():
        """Disconnect Xero integration"""
        manager = get_integration_manager()
        manager.disconnect(IntegrationType.XERO)
        return jsonify({'success': True})

    # Unified Data APIs
    @app.route('/api/integrations/invoices', methods=['GET'])
    def api_integration_invoices():
        """Get invoices from connected integrations"""
        manager = get_integration_manager()
        source = request.args.get('source')

        source_type = None
        if source:
            try:
                source_type = IntegrationType(source)
            except ValueError:
                return jsonify({'error': f'Invalid source: {source}'}), 400

        invoices = manager.get_invoices(source=source_type)
        return jsonify({
            'invoices': [
                {
                    'id': inv.id,
                    'source': inv.source.value,
                    'customer_name': inv.customer_name,
                    'invoice_number': inv.invoice_number,
                    'total_amount': inv.total_amount,
                    'amount_due': inv.amount_due,
                    'amount_paid': inv.amount_paid,
                    'issue_date': inv.issue_date.isoformat(),
                    'due_date': inv.due_date.isoformat() if inv.due_date else None,
                    'status': inv.status,
                    'days_outstanding': inv.days_outstanding
                }
                for inv in invoices
            ],
            'count': len(invoices)
        })

    @app.route('/api/integrations/bills', methods=['GET'])
    def api_integration_bills():
        """Get bills from connected integrations"""
        manager = get_integration_manager()
        source = request.args.get('source')

        source_type = None
        if source:
            try:
                source_type = IntegrationType(source)
            except ValueError:
                return jsonify({'error': f'Invalid source: {source}'}), 400

        bills = manager.get_bills(source=source_type)
        return jsonify({
            'bills': [
                {
                    'id': bill.id,
                    'source': bill.source.value,
                    'vendor_name': bill.vendor_name,
                    'bill_number': bill.bill_number,
                    'total_amount': bill.total_amount,
                    'amount_due': bill.amount_due,
                    'amount_paid': bill.amount_paid,
                    'issue_date': bill.issue_date.isoformat(),
                    'due_date': bill.due_date.isoformat() if bill.due_date else None,
                    'status': bill.status
                }
                for bill in bills
            ],
            'count': len(bills)
        })

    @app.route('/api/integrations/transactions', methods=['GET'])
    def api_integration_transactions():
        """Get bank transactions from connected integrations"""
        manager = get_integration_manager()
        transactions = manager.get_transactions()
        return jsonify({
            'transactions': [
                {
                    'id': txn.id,
                    'source': txn.source.value,
                    'date': txn.date.isoformat(),
                    'amount': txn.amount,
                    'description': txn.description,
                    'account_name': txn.account_name,
                    'transaction_type': txn.transaction_type,
                    'category': txn.category
                }
                for txn in transactions
            ],
            'count': len(transactions)
        })

    @app.route('/api/integrations/ar-aging', methods=['GET'])
    def api_integration_ar_aging():
        """Get AR aging report from integrations"""
        manager = get_integration_manager()
        aging = manager.get_ar_aging()
        return jsonify(aging)

    @app.route('/api/integrations/ap-aging', methods=['GET'])
    def api_integration_ap_aging():
        """Get AP aging report from integrations"""
        manager = get_integration_manager()
        aging = manager.get_ap_aging()
        return jsonify(aging)

    @app.route('/api/integrations/cash-flow-summary', methods=['GET'])
    def api_integration_cash_flow_summary():
        """Get unified cash flow summary from all integrations"""
        manager = get_integration_manager()
        days = request.args.get('days', 30, type=int)
        summary = manager.get_unified_cash_flow_summary(days=days)
        return jsonify(summary)

    # =============================================================================
    # Error Handlers
    # =============================================================================

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('404.html', app_name=app.config['APP_NAME']), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Server error: {e}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('500.html', app_name=app.config['APP_NAME']), 500

    return app


# =============================================================================
# Main
# =============================================================================

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5101))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(debug=debug, port=port, host='0.0.0.0')
