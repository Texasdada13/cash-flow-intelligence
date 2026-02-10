"""
Demo Data Generator for Cash Flow Intelligence

Generates realistic SMB financial data for demonstrations and testing.
Creates companies with 12 months of historical data, forecasts, and chat sessions.
"""

import random
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Industry configurations with realistic financial profiles
INDUSTRY_PROFILES = {
    "professional_services": {
        "name": "Professional Services",
        "revenue_range": (50000, 200000),
        "gross_margin": (0.60, 0.75),
        "payroll_ratio": (0.40, 0.55),
        "dso_range": (35, 60),
        "dpo_range": (20, 35),
        "growth_rate": (0.02, 0.08),
        "seasonality": [1.0, 0.95, 1.05, 1.10, 1.05, 0.95, 0.85, 0.90, 1.05, 1.15, 1.10, 0.85],
        "example_companies": [
            ("Apex Consulting Group", "Management consulting for mid-market companies"),
            ("Clarity Legal Partners", "Business law and contract services"),
            ("Summit Accounting Solutions", "CPA firm serving SMBs"),
        ]
    },
    "manufacturing": {
        "name": "Manufacturing",
        "revenue_range": (100000, 500000),
        "gross_margin": (0.25, 0.40),
        "payroll_ratio": (0.20, 0.30),
        "dso_range": (40, 65),
        "dpo_range": (35, 55),
        "growth_rate": (0.01, 0.05),
        "seasonality": [0.90, 0.85, 0.95, 1.05, 1.10, 1.15, 1.05, 1.00, 1.05, 1.10, 1.00, 0.80],
        "example_companies": [
            ("Precision Parts Inc", "Custom metal fabrication and machining"),
            ("GreenTech Manufacturing", "Sustainable packaging solutions"),
            ("Midwest Tool & Die", "Industrial tooling and dies"),
        ]
    },
    "retail": {
        "name": "Retail",
        "revenue_range": (75000, 300000),
        "gross_margin": (0.35, 0.50),
        "payroll_ratio": (0.15, 0.25),
        "dso_range": (5, 15),
        "dpo_range": (25, 45),
        "growth_rate": (0.00, 0.06),
        "seasonality": [0.70, 0.75, 0.85, 0.90, 0.95, 0.90, 0.85, 0.90, 0.95, 1.05, 1.35, 1.85],
        "example_companies": [
            ("Urban Home Furnishings", "Contemporary furniture and decor"),
            ("Outdoor Adventure Gear", "Camping and hiking equipment"),
            ("Sweet Delights Bakery", "Artisan bakery and cafe"),
        ]
    },
    "technology": {
        "name": "Technology",
        "revenue_range": (40000, 150000),
        "gross_margin": (0.70, 0.85),
        "payroll_ratio": (0.45, 0.60),
        "dso_range": (25, 45),
        "dpo_range": (20, 40),
        "growth_rate": (0.05, 0.15),
        "seasonality": [0.95, 0.90, 1.00, 1.05, 1.00, 0.95, 0.90, 0.95, 1.05, 1.10, 1.10, 1.05],
        "example_companies": [
            ("CloudSync Solutions", "SaaS platform for data integration"),
            ("CodeCraft Studios", "Custom software development"),
            ("DataPulse Analytics", "Business intelligence dashboards"),
        ]
    },
    "healthcare": {
        "name": "Healthcare",
        "revenue_range": (80000, 250000),
        "gross_margin": (0.45, 0.60),
        "payroll_ratio": (0.35, 0.50),
        "dso_range": (45, 75),
        "dpo_range": (25, 40),
        "growth_rate": (0.03, 0.08),
        "seasonality": [1.05, 0.95, 1.00, 1.00, 1.00, 0.95, 0.90, 0.95, 1.00, 1.05, 1.05, 1.10],
        "example_companies": [
            ("Wellness First Clinic", "Primary care and preventive health"),
            ("Peak Physical Therapy", "Sports and rehabilitation therapy"),
            ("MindBridge Counseling", "Mental health services"),
        ]
    },
    "construction": {
        "name": "Construction",
        "revenue_range": (150000, 600000),
        "gross_margin": (0.20, 0.35),
        "payroll_ratio": (0.25, 0.40),
        "dso_range": (50, 80),
        "dpo_range": (40, 60),
        "growth_rate": (0.02, 0.07),
        "seasonality": [0.60, 0.65, 0.85, 1.10, 1.25, 1.30, 1.25, 1.20, 1.10, 0.95, 0.75, 0.55],
        "example_companies": [
            ("Cornerstone Builders", "Commercial construction and renovation"),
            ("EcoHome Construction", "Sustainable residential building"),
            ("Metro Electrical Services", "Commercial electrical contracting"),
        ]
    }
}

# Risk scenarios for demo data
RISK_SCENARIOS = {
    "healthy": {
        "description": "Strong cash position with good runway",
        "cash_buffer_months": (4, 8),
        "health_score_range": (70, 90),
        "ar_collection_efficiency": (0.85, 0.95),
        "expense_variance": (0.95, 1.05)
    },
    "moderate_risk": {
        "description": "Some cash pressure, needs attention",
        "cash_buffer_months": (2, 4),
        "health_score_range": (45, 65),
        "ar_collection_efficiency": (0.70, 0.85),
        "expense_variance": (1.00, 1.15)
    },
    "high_risk": {
        "description": "Cash crunch situation, urgent action needed",
        "cash_buffer_months": (0.5, 2),
        "health_score_range": (20, 45),
        "ar_collection_efficiency": (0.55, 0.70),
        "expense_variance": (1.10, 1.25)
    }
}


@dataclass
class GeneratedCompany:
    """Generated company data structure"""
    company: Dict[str, Any]
    financial_periods: List[Dict[str, Any]]
    cash_flow_entries: List[Dict[str, Any]]
    forecasts: List[Dict[str, Any]]
    health_summary: Dict[str, Any]


class DemoDataGenerator:
    """
    Generate realistic demo data for Cash Flow Intelligence.

    Creates complete company profiles with:
    - 12 months of historical financial data
    - Cash flow entries
    - Forecasts with multiple scenarios
    - Health score calculations

    Example:
        generator = DemoDataGenerator()

        # Generate a healthy tech company
        company = generator.generate_company(
            industry="technology",
            risk_scenario="healthy"
        )

        # Generate multiple demo companies
        companies = generator.generate_demo_set()
    """

    def __init__(self, seed: Optional[int] = None):
        """Initialize generator with optional random seed for reproducibility"""
        if seed is not None:
            random.seed(seed)

    def generate_company(
        self,
        industry: str = "professional_services",
        risk_scenario: str = "healthy",
        company_name: Optional[str] = None,
        months_of_history: int = 12
    ) -> GeneratedCompany:
        """
        Generate a complete company with financial history.

        Args:
            industry: Industry type (see INDUSTRY_PROFILES)
            risk_scenario: Risk level (healthy, moderate_risk, high_risk)
            company_name: Optional custom name
            months_of_history: Number of months of data to generate

        Returns:
            GeneratedCompany with all data populated
        """
        profile = INDUSTRY_PROFILES.get(industry, INDUSTRY_PROFILES["professional_services"])
        risk = RISK_SCENARIOS.get(risk_scenario, RISK_SCENARIOS["healthy"])

        # Generate company info
        if company_name is None:
            example = random.choice(profile["example_companies"])
            company_name = example[0]
            description = example[1]
        else:
            description = f"{company_name} - {profile['name']} company"

        company_id = str(uuid.uuid4())

        # Base financial parameters
        base_revenue = random.uniform(*profile["revenue_range"])
        gross_margin = random.uniform(*profile["gross_margin"])
        payroll_ratio = random.uniform(*profile["payroll_ratio"])
        monthly_growth = random.uniform(*profile["growth_rate"]) / 12

        # Generate financial periods
        periods = []
        cash_entries = []

        today = date.today()
        start_date = date(today.year - 1, today.month, 1)

        # Starting cash position based on risk scenario
        cash_buffer = random.uniform(*risk["cash_buffer_months"])
        monthly_expenses = base_revenue * (1 - gross_margin) + (base_revenue * payroll_ratio)
        current_cash = monthly_expenses * cash_buffer

        for month_offset in range(months_of_history):
            period_date = date(
                start_date.year + (start_date.month + month_offset - 1) // 12,
                (start_date.month + month_offset - 1) % 12 + 1,
                1
            )

            # Apply seasonality and growth
            season_idx = period_date.month - 1
            seasonality = profile["seasonality"][season_idx]
            growth_factor = 1 + (monthly_growth * month_offset)

            # Revenue with variance
            revenue = base_revenue * seasonality * growth_factor
            revenue *= random.uniform(0.92, 1.08)  # Random variance

            # Apply risk scenario effects
            collection_efficiency = random.uniform(*risk["ar_collection_efficiency"])
            expense_factor = random.uniform(*risk["expense_variance"])

            # Cost structure
            cogs = revenue * (1 - gross_margin)
            gross_profit = revenue - cogs

            payroll = revenue * payroll_ratio * expense_factor
            rent = base_revenue * 0.08  # Fixed rent
            utilities = base_revenue * 0.02
            marketing = revenue * random.uniform(0.03, 0.08)
            other_expenses = revenue * random.uniform(0.05, 0.10) * expense_factor

            operating_expenses = payroll + rent + utilities + marketing + other_expenses
            operating_income = gross_profit - operating_expenses

            interest_expense = base_revenue * random.uniform(0.01, 0.03)
            net_income = operating_income - interest_expense

            # Balance sheet items
            dso = random.uniform(*profile["dso_range"])
            dpo = random.uniform(*profile["dpo_range"])

            accounts_receivable = (revenue / 30) * dso
            accounts_payable = (cogs / 30) * dpo

            inventory = cogs * random.uniform(0.5, 1.5) if industry in ["manufacturing", "retail"] else 0

            # Cash flow calculation
            cash_inflow = revenue * collection_efficiency
            cash_outflow = operating_expenses + cogs * 0.7 + interest_expense
            net_cash_flow = cash_inflow - cash_outflow
            current_cash = max(0, current_cash + net_cash_flow)

            # Build period record
            period_id = str(uuid.uuid4())
            period = {
                "id": period_id,
                "company_id": company_id,
                "period_type": "monthly",
                "period_date": period_date.isoformat(),
                "period_label": period_date.strftime("%b %Y"),

                # Income statement
                "revenue": round(revenue, 2),
                "cogs": round(cogs, 2),
                "gross_profit": round(gross_profit, 2),
                "operating_expenses": round(operating_expenses, 2),
                "payroll": round(payroll, 2),
                "rent": round(rent, 2),
                "utilities": round(utilities, 2),
                "marketing": round(marketing, 2),
                "other_expenses": round(other_expenses, 2),
                "operating_income": round(operating_income, 2),
                "interest_expense": round(interest_expense, 2),
                "net_income": round(net_income, 2),

                # Balance sheet
                "cash": round(current_cash, 2),
                "accounts_receivable": round(accounts_receivable, 2),
                "inventory": round(inventory, 2),
                "other_current_assets": round(revenue * 0.05, 2),
                "total_current_assets": round(current_cash + accounts_receivable + inventory + revenue * 0.05, 2),
                "fixed_assets": round(base_revenue * 2, 2),
                "total_assets": round(current_cash + accounts_receivable + inventory + revenue * 0.05 + base_revenue * 2, 2),

                "accounts_payable": round(accounts_payable, 2),
                "short_term_debt": round(base_revenue * 0.5, 2),
                "accrued_expenses": round(payroll * 0.3, 2),
                "total_current_liabilities": round(accounts_payable + base_revenue * 0.5 + payroll * 0.3, 2),
                "long_term_debt": round(base_revenue * 1.5, 2),
                "total_liabilities": round(accounts_payable + base_revenue * 0.5 + payroll * 0.3 + base_revenue * 1.5, 2),
                "total_equity": round(base_revenue * 2, 2),

                # Metrics
                "current_ratio": round((current_cash + accounts_receivable + inventory) /
                                      (accounts_payable + base_revenue * 0.5 + payroll * 0.3), 2),
                "quick_ratio": round((current_cash + accounts_receivable) /
                                    (accounts_payable + base_revenue * 0.5 + payroll * 0.3), 2),
                "gross_margin": round((gross_profit / revenue) * 100, 1),
                "net_margin": round((net_income / revenue) * 100, 1),
                "days_sales_outstanding": round(dso, 1),
                "days_payables_outstanding": round(dpo, 1),
                "cash_conversion_cycle": round(dso - dpo + (inventory / (cogs / 30) if cogs > 0 else 0), 1)
            }
            periods.append(period)

            # Generate cash flow entries
            entries = self._generate_cash_entries(period_id, period_date, revenue,
                                                   payroll, rent, cogs, marketing)
            cash_entries.extend(entries)

        # Calculate health summary
        latest_period = periods[-1]
        health_score = random.uniform(*risk["health_score_range"])

        avg_net_income = sum(p["net_income"] for p in periods) / len(periods)
        monthly_burn = -avg_net_income if avg_net_income < 0 else 0
        runway = (latest_period["cash"] / monthly_burn) if monthly_burn > 0 else 24

        health_summary = {
            "health_score": round(health_score, 1),
            "risk_level": "low" if health_score >= 70 else ("medium" if health_score >= 45 else "high"),
            "cash_runway_months": round(min(runway, 24), 1),
            "current_cash": latest_period["cash"],
            "monthly_burn": round(monthly_burn, 2),
            "dso": latest_period["days_sales_outstanding"],
            "dpo": latest_period["days_payables_outstanding"],
            "key_metrics": {
                "current_ratio": latest_period["current_ratio"],
                "quick_ratio": latest_period["quick_ratio"],
                "gross_margin": latest_period["gross_margin"],
                "net_margin": latest_period["net_margin"]
            },
            "top_concerns": self._generate_concerns(health_score, latest_period, profile),
            "recommendations": self._generate_recommendations(health_score, latest_period, profile)
        }

        # Generate forecasts
        forecasts = self._generate_forecasts(company_id, periods, profile, risk)

        # Build company record
        company = {
            "id": company_id,
            "name": company_name,
            "industry": profile["name"],
            "description": description,
            "revenue_range": self._get_revenue_range_label(base_revenue * 12),
            "employee_count": self._estimate_employees(base_revenue, payroll_ratio),
            "founded_year": random.randint(2005, 2020),
            "fiscal_year_end": "12-31",
            "contact_name": self._generate_contact_name(),
            "contact_email": f"finance@{company_name.lower().replace(' ', '')}.com",
            "health_score": health_summary["health_score"],
            "risk_level": health_summary["risk_level"],
            "cash_runway_months": health_summary["cash_runway_months"],
            "last_analysis_date": datetime.now().isoformat()
        }

        return GeneratedCompany(
            company=company,
            financial_periods=periods,
            cash_flow_entries=cash_entries,
            forecasts=forecasts,
            health_summary=health_summary
        )

    def _generate_cash_entries(
        self,
        period_id: str,
        period_date: date,
        revenue: float,
        payroll: float,
        rent: float,
        cogs: float,
        marketing: float
    ) -> List[Dict]:
        """Generate detailed cash flow entries for a period"""
        entries = []

        # Revenue collections (split across month)
        for week in range(4):
            entry_date = period_date + timedelta(days=7 * week + random.randint(0, 3))
            entries.append({
                "id": str(uuid.uuid4()),
                "period_id": period_id,
                "entry_date": entry_date.isoformat(),
                "entry_type": "inflow",
                "category": "operating",
                "subcategory": "collections",
                "description": f"Customer collections - Week {week + 1}",
                "amount": round(revenue * random.uniform(0.20, 0.30), 2),
                "is_recurring": True,
                "recurrence_pattern": "weekly"
            })

        # Payroll (bi-weekly)
        for pay_period in range(2):
            entry_date = period_date + timedelta(days=14 * pay_period + 14)
            entries.append({
                "id": str(uuid.uuid4()),
                "period_id": period_id,
                "entry_date": entry_date.isoformat(),
                "entry_type": "outflow",
                "category": "operating",
                "subcategory": "payroll",
                "description": f"Payroll - Period {pay_period + 1}",
                "amount": round(payroll / 2, 2),
                "is_recurring": True,
                "recurrence_pattern": "bi-weekly"
            })

        # Fixed expenses
        entries.append({
            "id": str(uuid.uuid4()),
            "period_id": period_id,
            "entry_date": (period_date + timedelta(days=1)).isoformat(),
            "entry_type": "outflow",
            "category": "operating",
            "subcategory": "rent",
            "description": "Monthly rent payment",
            "amount": round(rent, 2),
            "is_recurring": True,
            "recurrence_pattern": "monthly"
        })

        # Supplier payments
        entries.append({
            "id": str(uuid.uuid4()),
            "period_id": period_id,
            "entry_date": (period_date + timedelta(days=15)).isoformat(),
            "entry_type": "outflow",
            "category": "operating",
            "subcategory": "suppliers",
            "description": "Supplier payments",
            "amount": round(cogs * 0.7, 2),
            "is_recurring": False,
            "recurrence_pattern": None
        })

        # Marketing spend
        entries.append({
            "id": str(uuid.uuid4()),
            "period_id": period_id,
            "entry_date": (period_date + timedelta(days=10)).isoformat(),
            "entry_type": "outflow",
            "category": "operating",
            "subcategory": "marketing",
            "description": "Marketing and advertising",
            "amount": round(marketing, 2),
            "is_recurring": True,
            "recurrence_pattern": "monthly"
        })

        return entries

    def _generate_forecasts(
        self,
        company_id: str,
        periods: List[Dict],
        profile: Dict,
        risk: Dict
    ) -> List[Dict]:
        """Generate forecast data for multiple scenarios"""
        forecasts = []
        scenarios = ["baseline", "optimistic", "pessimistic"]

        latest_cash = periods[-1]["cash"]
        avg_net_flow = sum(p["net_income"] for p in periods[-3:]) / 3

        for scenario in scenarios:
            forecast_id = str(uuid.uuid4())

            # Adjust projections by scenario
            if scenario == "optimistic":
                flow_adjustment = 1.20
            elif scenario == "pessimistic":
                flow_adjustment = 0.80
            else:
                flow_adjustment = 1.0

            adjusted_flow = avg_net_flow * flow_adjustment

            # Calculate 6-month forecast
            forecast_data = []
            projected_cash = latest_cash

            for month in range(1, 7):
                future_date = date.today() + timedelta(days=30 * month)
                projected_cash += adjusted_flow

                forecast_data.append({
                    "date": future_date.isoformat(),
                    "predicted_cash": round(max(0, projected_cash), 2),
                    "lower_bound": round(max(0, projected_cash * 0.85), 2),
                    "upper_bound": round(projected_cash * 1.15, 2)
                })

            # Find zero cash date if applicable
            zero_date = None
            if adjusted_flow < 0:
                months_to_zero = latest_cash / abs(adjusted_flow)
                if months_to_zero < 12:
                    zero_date = (date.today() + timedelta(days=30 * months_to_zero)).isoformat()

            forecasts.append({
                "id": forecast_id,
                "company_id": company_id,
                "forecast_date": datetime.now().isoformat(),
                "scenario": scenario,
                "model_type": "statistical",
                "periods_forecast": 6,
                "confidence_level": 0.80,
                "runway_months": round(latest_cash / abs(adjusted_flow) if adjusted_flow < 0 else 24, 1),
                "zero_cash_date": zero_date,
                "ending_cash_predicted": forecast_data[-1]["predicted_cash"],
                "forecast_data": forecast_data
            })

        return forecasts

    def _generate_concerns(
        self,
        health_score: float,
        period: Dict,
        profile: Dict
    ) -> List[str]:
        """Generate relevant concerns based on metrics"""
        concerns = []

        if health_score < 50:
            concerns.append("Cash runway below comfortable threshold")

        if period["days_sales_outstanding"] > profile["dso_range"][1]:
            concerns.append(f"DSO of {period['days_sales_outstanding']} days exceeds industry average")

        if period["net_margin"] < 5:
            concerns.append("Net margin is below sustainable levels")

        if period["current_ratio"] < 1.2:
            concerns.append("Current ratio indicates potential liquidity pressure")

        if period["quick_ratio"] < 1.0:
            concerns.append("Quick ratio suggests difficulty meeting short-term obligations")

        if not concerns:
            concerns.append("No critical concerns identified")

        return concerns[:3]  # Top 3 concerns

    def _generate_recommendations(
        self,
        health_score: float,
        period: Dict,
        profile: Dict
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if period["days_sales_outstanding"] > 40:
            recommendations.append("Implement stricter collection procedures to reduce DSO")

        if period["net_margin"] < 10:
            recommendations.append("Review pricing strategy and cost structure")

        if health_score < 60:
            recommendations.append("Build cash reserves through expense optimization")

        if period["days_payables_outstanding"] < 30:
            recommendations.append("Consider negotiating extended payment terms with suppliers")

        recommendations.append("Maintain 3-6 months of operating expenses as cash reserve")

        return recommendations[:4]

    def _get_revenue_range_label(self, annual_revenue: float) -> str:
        """Convert annual revenue to range label"""
        if annual_revenue < 500000:
            return "Under $500K"
        elif annual_revenue < 1000000:
            return "$500K-$1M"
        elif annual_revenue < 2500000:
            return "$1M-$2.5M"
        elif annual_revenue < 5000000:
            return "$2.5M-$5M"
        elif annual_revenue < 10000000:
            return "$5M-$10M"
        else:
            return "$10M+"

    def _estimate_employees(self, monthly_revenue: float, payroll_ratio: float) -> int:
        """Estimate employee count from payroll"""
        annual_payroll = monthly_revenue * payroll_ratio * 12
        avg_salary = 65000  # Assumed average
        return max(1, int(annual_payroll / avg_salary))

    def _generate_contact_name(self) -> str:
        """Generate a realistic contact name"""
        first_names = ["Michael", "Sarah", "David", "Jennifer", "Robert", "Lisa",
                      "James", "Patricia", "John", "Elizabeth"]
        last_names = ["Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                     "Davis", "Rodriguez", "Martinez", "Anderson"]
        return f"{random.choice(first_names)} {random.choice(last_names)}"

    def generate_demo_set(self, count: int = 6) -> List[GeneratedCompany]:
        """
        Generate a diverse set of demo companies.

        Creates companies across different industries and risk levels
        for a comprehensive demo experience.
        """
        companies = []

        # Predefined mix for good demo coverage
        demo_configs = [
            ("technology", "healthy"),
            ("professional_services", "healthy"),
            ("manufacturing", "moderate_risk"),
            ("retail", "moderate_risk"),
            ("healthcare", "high_risk"),
            ("construction", "healthy"),
        ]

        for i, (industry, risk) in enumerate(demo_configs[:count]):
            company = self.generate_company(industry=industry, risk_scenario=risk)
            companies.append(company)

        return companies


def load_demo_data_to_db(db_session, count: int = 3) -> List[str]:
    """
    Load demo data directly into the database.

    Args:
        db_session: SQLAlchemy database session
        count: Number of demo companies to create

    Returns:
        List of created company IDs
    """
    from .database.models import Company, FinancialPeriod, CashFlowEntry, Forecast

    generator = DemoDataGenerator(seed=42)  # Reproducible demos
    companies = generator.generate_demo_set(count=count)
    company_ids = []

    for gen_company in companies:
        # Create company
        company = Company(
            id=gen_company.company["id"],
            name=gen_company.company["name"],
            industry=gen_company.company["industry"],
            description=gen_company.company["description"],
            revenue_range=gen_company.company["revenue_range"],
            employee_count=gen_company.company["employee_count"],
            founded_year=gen_company.company["founded_year"],
            fiscal_year_end=gen_company.company["fiscal_year_end"],
            contact_name=gen_company.company["contact_name"],
            contact_email=gen_company.company["contact_email"],
            health_score=gen_company.company["health_score"],
            risk_level=gen_company.company["risk_level"],
            cash_runway_months=gen_company.company["cash_runway_months"]
        )
        db_session.add(company)

        # Create financial periods
        for period_data in gen_company.financial_periods:
            period = FinancialPeriod(
                id=period_data["id"],
                company_id=period_data["company_id"],
                period_type=period_data["period_type"],
                period_date=date.fromisoformat(period_data["period_date"]),
                period_label=period_data["period_label"],
                revenue=period_data["revenue"],
                cogs=period_data["cogs"],
                gross_profit=period_data["gross_profit"],
                operating_expenses=period_data["operating_expenses"],
                payroll=period_data["payroll"],
                rent=period_data["rent"],
                utilities=period_data["utilities"],
                marketing=period_data["marketing"],
                other_expenses=period_data["other_expenses"],
                operating_income=period_data["operating_income"],
                interest_expense=period_data["interest_expense"],
                net_income=period_data["net_income"],
                cash=period_data["cash"],
                accounts_receivable=period_data["accounts_receivable"],
                inventory=period_data["inventory"],
                accounts_payable=period_data["accounts_payable"],
                current_ratio=period_data["current_ratio"],
                quick_ratio=period_data["quick_ratio"],
                gross_margin=period_data["gross_margin"],
                net_margin=period_data["net_margin"],
                days_sales_outstanding=period_data["days_sales_outstanding"],
                days_payables_outstanding=period_data["days_payables_outstanding"]
            )
            db_session.add(period)

            # Create cash flow entries
            for entry_data in [e for e in gen_company.cash_flow_entries
                              if e["period_id"] == period_data["id"]]:
                entry = CashFlowEntry(
                    id=entry_data["id"],
                    period_id=entry_data["period_id"],
                    entry_date=date.fromisoformat(entry_data["entry_date"]),
                    entry_type=entry_data["entry_type"],
                    category=entry_data["category"],
                    subcategory=entry_data["subcategory"],
                    description=entry_data["description"],
                    amount=entry_data["amount"],
                    is_recurring=entry_data["is_recurring"],
                    recurrence_pattern=entry_data["recurrence_pattern"]
                )
                db_session.add(entry)

        # Create forecasts
        for forecast_data in gen_company.forecasts:
            forecast = Forecast(
                id=forecast_data["id"],
                company_id=forecast_data["company_id"],
                scenario=forecast_data["scenario"],
                model_type=forecast_data["model_type"],
                periods_forecast=forecast_data["periods_forecast"],
                confidence_level=forecast_data["confidence_level"],
                runway_months=forecast_data["runway_months"],
                zero_cash_date=date.fromisoformat(forecast_data["zero_cash_date"])
                              if forecast_data["zero_cash_date"] else None,
                ending_cash_predicted=forecast_data["ending_cash_predicted"],
                forecast_data=forecast_data["forecast_data"]
            )
            db_session.add(forecast)

        company_ids.append(gen_company.company["id"])

    db_session.commit()
    return company_ids


# Quick test function
if __name__ == "__main__":
    generator = DemoDataGenerator(seed=42)
    company = generator.generate_company(
        industry="technology",
        risk_scenario="moderate_risk"
    )

    print(f"Generated: {company.company['name']}")
    print(f"Industry: {company.company['industry']}")
    print(f"Health Score: {company.health_summary['health_score']}")
    print(f"Cash Runway: {company.health_summary['cash_runway_months']} months")
    print(f"Periods: {len(company.financial_periods)}")
    print(f"Cash Entries: {len(company.cash_flow_entries)}")
    print(f"Forecasts: {len(company.forecasts)}")
