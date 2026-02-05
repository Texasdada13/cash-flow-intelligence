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
from src.database.models import db, Company, FinancialPeriod, CashFlowEntry, Forecast, ChatSession
from src.ai_core.chat_engine import AIChatEngine, ConversationMode, get_chat_engine
from src.patterns.weighted_scoring import create_smb_cash_flow_engine
from src.patterns.benchmark_engine import create_cash_flow_benchmarks
from src.patterns.risk_classification import create_cash_flow_risk_classifier

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
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(debug=debug, port=port, host='0.0.0.0')
