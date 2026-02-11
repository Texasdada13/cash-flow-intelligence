"""
QuickBooks Online Integration Client

Provides OAuth2 authentication and data fetching for:
- Invoices (Accounts Receivable)
- Bills (Accounts Payable)
- Bank Transactions
- Profit & Loss Reports
- Balance Sheet
- Cash Flow Statements
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import requests
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class QuickBooksEnvironment(Enum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"


@dataclass
class QuickBooksConfig:
    """Configuration for QuickBooks OAuth and API access"""
    client_id: str
    client_secret: str
    redirect_uri: str
    environment: QuickBooksEnvironment = QuickBooksEnvironment.SANDBOX

    @property
    def auth_base_url(self) -> str:
        return "https://appcenter.intuit.com/connect/oauth2"

    @property
    def token_url(self) -> str:
        return "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

    @property
    def api_base_url(self) -> str:
        if self.environment == QuickBooksEnvironment.SANDBOX:
            return "https://sandbox-quickbooks.api.intuit.com"
        return "https://quickbooks.api.intuit.com"

    @classmethod
    def from_env(cls) -> 'QuickBooksConfig':
        """Create config from environment variables"""
        return cls(
            client_id=os.getenv('QUICKBOOKS_CLIENT_ID', ''),
            client_secret=os.getenv('QUICKBOOKS_CLIENT_SECRET', ''),
            redirect_uri=os.getenv('QUICKBOOKS_REDIRECT_URI', 'http://localhost:5101/integrations/quickbooks/callback'),
            environment=QuickBooksEnvironment(os.getenv('QUICKBOOKS_ENVIRONMENT', 'sandbox'))
        )


@dataclass
class QuickBooksToken:
    """OAuth token storage"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    created_at: datetime = field(default_factory=datetime.utcnow)
    realm_id: str = ""

    @property
    def is_expired(self) -> bool:
        expiry = self.created_at + timedelta(seconds=self.expires_in - 60)
        return datetime.utcnow() >= expiry

    def to_dict(self) -> Dict[str, Any]:
        return {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_type': self.token_type,
            'expires_in': self.expires_in,
            'created_at': self.created_at.isoformat(),
            'realm_id': self.realm_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuickBooksToken':
        return cls(
            access_token=data['access_token'],
            refresh_token=data['refresh_token'],
            token_type=data.get('token_type', 'Bearer'),
            expires_in=data.get('expires_in', 3600),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.utcnow(),
            realm_id=data.get('realm_id', '')
        )


@dataclass
class Invoice:
    """QuickBooks Invoice representation"""
    id: str
    customer_name: str
    amount: float
    balance: float
    due_date: Optional[datetime]
    create_date: datetime
    status: str  # Paid, Open, Overdue
    line_items: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_overdue(self) -> bool:
        if self.due_date and self.balance > 0:
            return datetime.utcnow() > self.due_date
        return False

    @property
    def days_outstanding(self) -> int:
        return (datetime.utcnow() - self.create_date).days


@dataclass
class Bill:
    """QuickBooks Bill (AP) representation"""
    id: str
    vendor_name: str
    amount: float
    balance: float
    due_date: Optional[datetime]
    create_date: datetime
    status: str
    line_items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class BankTransaction:
    """Bank transaction representation"""
    id: str
    date: datetime
    amount: float
    description: str
    account_name: str
    transaction_type: str  # Deposit, Withdrawal, Transfer
    category: Optional[str] = None
    is_reconciled: bool = False


class QuickBooksClient:
    """
    QuickBooks Online API Client

    Handles OAuth2 authentication and provides methods for fetching
    financial data relevant to cash flow analysis.
    """

    def __init__(self, config: QuickBooksConfig):
        self.config = config
        self.token: Optional[QuickBooksToken] = None
        self._session = requests.Session()

    # ========== OAuth Methods ==========

    def get_authorization_url(self, state: str = "") -> str:
        """Generate OAuth authorization URL for user consent"""
        params = {
            'client_id': self.config.client_id,
            'response_type': 'code',
            'scope': 'com.intuit.quickbooks.accounting',
            'redirect_uri': self.config.redirect_uri,
            'state': state
        }
        return f"{self.config.auth_base_url}?{urlencode(params)}"

    def exchange_code_for_token(self, authorization_code: str, realm_id: str) -> QuickBooksToken:
        """Exchange authorization code for access token"""
        response = self._session.post(
            self.config.token_url,
            auth=(self.config.client_id, self.config.client_secret),
            data={
                'grant_type': 'authorization_code',
                'code': authorization_code,
                'redirect_uri': self.config.redirect_uri
            }
        )
        response.raise_for_status()
        data = response.json()

        self.token = QuickBooksToken(
            access_token=data['access_token'],
            refresh_token=data['refresh_token'],
            token_type=data.get('token_type', 'Bearer'),
            expires_in=data.get('expires_in', 3600),
            realm_id=realm_id
        )
        return self.token

    def refresh_access_token(self) -> QuickBooksToken:
        """Refresh the access token using refresh token"""
        if not self.token:
            raise ValueError("No token available to refresh")

        response = self._session.post(
            self.config.token_url,
            auth=(self.config.client_id, self.config.client_secret),
            data={
                'grant_type': 'refresh_token',
                'refresh_token': self.token.refresh_token
            }
        )
        response.raise_for_status()
        data = response.json()

        self.token = QuickBooksToken(
            access_token=data['access_token'],
            refresh_token=data.get('refresh_token', self.token.refresh_token),
            token_type=data.get('token_type', 'Bearer'),
            expires_in=data.get('expires_in', 3600),
            realm_id=self.token.realm_id
        )
        return self.token

    def set_token(self, token: QuickBooksToken):
        """Set token from stored credentials"""
        self.token = token

    def _ensure_valid_token(self):
        """Ensure we have a valid, non-expired token"""
        if not self.token:
            raise ValueError("No token set. Please authenticate first.")
        if self.token.is_expired:
            self.refresh_access_token()

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated API request"""
        self._ensure_valid_token()

        url = f"{self.config.api_base_url}/v3/company/{self.token.realm_id}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.token.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        response = self._session.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    # ========== Invoice (AR) Methods ==========

    def get_invoices(self, start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None,
                     status: Optional[str] = None) -> List[Invoice]:
        """Fetch invoices (Accounts Receivable)"""
        query = "SELECT * FROM Invoice"
        conditions = []

        if start_date:
            conditions.append(f"TxnDate >= '{start_date.strftime('%Y-%m-%d')}'")
        if end_date:
            conditions.append(f"TxnDate <= '{end_date.strftime('%Y-%m-%d')}'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDERBY TxnDate DESC MAXRESULTS 1000"

        data = self._make_request('GET', f'query?query={query}')
        invoices = []

        for inv in data.get('QueryResponse', {}).get('Invoice', []):
            due_date = None
            if inv.get('DueDate'):
                due_date = datetime.strptime(inv['DueDate'], '%Y-%m-%d')

            invoice = Invoice(
                id=inv['Id'],
                customer_name=inv.get('CustomerRef', {}).get('name', 'Unknown'),
                amount=float(inv.get('TotalAmt', 0)),
                balance=float(inv.get('Balance', 0)),
                due_date=due_date,
                create_date=datetime.strptime(inv['TxnDate'], '%Y-%m-%d'),
                status='Paid' if float(inv.get('Balance', 0)) == 0 else 'Open',
                line_items=inv.get('Line', [])
            )
            if invoice.is_overdue:
                invoice.status = 'Overdue'
            invoices.append(invoice)

        return invoices

    def get_ar_aging(self) -> Dict[str, Any]:
        """Get Accounts Receivable aging summary"""
        invoices = self.get_invoices()

        aging = {
            'current': 0,
            '1_30_days': 0,
            '31_60_days': 0,
            '61_90_days': 0,
            'over_90_days': 0,
            'total': 0
        }

        for inv in invoices:
            if inv.balance > 0:
                days = inv.days_outstanding
                if days <= 0:
                    aging['current'] += inv.balance
                elif days <= 30:
                    aging['1_30_days'] += inv.balance
                elif days <= 60:
                    aging['31_60_days'] += inv.balance
                elif days <= 90:
                    aging['61_90_days'] += inv.balance
                else:
                    aging['over_90_days'] += inv.balance
                aging['total'] += inv.balance

        return aging

    # ========== Bill (AP) Methods ==========

    def get_bills(self, start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> List[Bill]:
        """Fetch bills (Accounts Payable)"""
        query = "SELECT * FROM Bill"
        conditions = []

        if start_date:
            conditions.append(f"TxnDate >= '{start_date.strftime('%Y-%m-%d')}'")
        if end_date:
            conditions.append(f"TxnDate <= '{end_date.strftime('%Y-%m-%d')}'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDERBY TxnDate DESC MAXRESULTS 1000"

        data = self._make_request('GET', f'query?query={query}')
        bills = []

        for bill_data in data.get('QueryResponse', {}).get('Bill', []):
            due_date = None
            if bill_data.get('DueDate'):
                due_date = datetime.strptime(bill_data['DueDate'], '%Y-%m-%d')

            bill = Bill(
                id=bill_data['Id'],
                vendor_name=bill_data.get('VendorRef', {}).get('name', 'Unknown'),
                amount=float(bill_data.get('TotalAmt', 0)),
                balance=float(bill_data.get('Balance', 0)),
                due_date=due_date,
                create_date=datetime.strptime(bill_data['TxnDate'], '%Y-%m-%d'),
                status='Paid' if float(bill_data.get('Balance', 0)) == 0 else 'Open',
                line_items=bill_data.get('Line', [])
            )
            bills.append(bill)

        return bills

    def get_ap_aging(self) -> Dict[str, Any]:
        """Get Accounts Payable aging summary"""
        bills = self.get_bills()

        aging = {
            'current': 0,
            '1_30_days': 0,
            '31_60_days': 0,
            '61_90_days': 0,
            'over_90_days': 0,
            'total': 0
        }

        for bill in bills:
            if bill.balance > 0:
                days = (datetime.utcnow() - bill.create_date).days
                if days <= 0:
                    aging['current'] += bill.balance
                elif days <= 30:
                    aging['1_30_days'] += bill.balance
                elif days <= 60:
                    aging['31_60_days'] += bill.balance
                elif days <= 90:
                    aging['61_90_days'] += bill.balance
                else:
                    aging['over_90_days'] += bill.balance
                aging['total'] += bill.balance

        return aging

    # ========== Bank Transactions ==========

    def get_bank_transactions(self, account_id: Optional[str] = None,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> List[BankTransaction]:
        """Fetch bank transactions"""
        # Get deposits
        deposits = self._get_deposits(start_date, end_date)

        # Get purchases/withdrawals
        purchases = self._get_purchases(start_date, end_date)

        transactions = deposits + purchases
        transactions.sort(key=lambda x: x.date, reverse=True)

        return transactions

    def _get_deposits(self, start_date: Optional[datetime],
                      end_date: Optional[datetime]) -> List[BankTransaction]:
        """Fetch deposit transactions"""
        query = "SELECT * FROM Deposit"
        conditions = []

        if start_date:
            conditions.append(f"TxnDate >= '{start_date.strftime('%Y-%m-%d')}'")
        if end_date:
            conditions.append(f"TxnDate <= '{end_date.strftime('%Y-%m-%d')}'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " MAXRESULTS 500"

        data = self._make_request('GET', f'query?query={query}')
        transactions = []

        for dep in data.get('QueryResponse', {}).get('Deposit', []):
            transactions.append(BankTransaction(
                id=dep['Id'],
                date=datetime.strptime(dep['TxnDate'], '%Y-%m-%d'),
                amount=float(dep.get('TotalAmt', 0)),
                description=dep.get('PrivateNote', 'Deposit'),
                account_name=dep.get('DepositToAccountRef', {}).get('name', 'Unknown'),
                transaction_type='Deposit'
            ))

        return transactions

    def _get_purchases(self, start_date: Optional[datetime],
                       end_date: Optional[datetime]) -> List[BankTransaction]:
        """Fetch purchase/withdrawal transactions"""
        query = "SELECT * FROM Purchase"
        conditions = []

        if start_date:
            conditions.append(f"TxnDate >= '{start_date.strftime('%Y-%m-%d')}'")
        if end_date:
            conditions.append(f"TxnDate <= '{end_date.strftime('%Y-%m-%d')}'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " MAXRESULTS 500"

        data = self._make_request('GET', f'query?query={query}')
        transactions = []

        for purch in data.get('QueryResponse', {}).get('Purchase', []):
            transactions.append(BankTransaction(
                id=purch['Id'],
                date=datetime.strptime(purch['TxnDate'], '%Y-%m-%d'),
                amount=-float(purch.get('TotalAmt', 0)),  # Negative for outflows
                description=purch.get('PrivateNote', '') or purch.get('EntityRef', {}).get('name', 'Purchase'),
                account_name=purch.get('AccountRef', {}).get('name', 'Unknown'),
                transaction_type='Withdrawal'
            ))

        return transactions

    # ========== Reports ==========

    def get_profit_and_loss(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Fetch Profit & Loss report"""
        params = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }

        data = self._make_request('GET', f'reports/ProfitAndLoss?{urlencode(params)}')
        return self._parse_report(data)

    def get_balance_sheet(self, as_of_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Fetch Balance Sheet report"""
        params = {}
        if as_of_date:
            params['as_of'] = as_of_date.strftime('%Y-%m-%d')

        endpoint = 'reports/BalanceSheet'
        if params:
            endpoint += f'?{urlencode(params)}'

        data = self._make_request('GET', endpoint)
        return self._parse_report(data)

    def get_cash_flow_statement(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Fetch Cash Flow Statement"""
        params = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }

        data = self._make_request('GET', f'reports/CashFlow?{urlencode(params)}')
        return self._parse_report(data)

    def _parse_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse QuickBooks report format into structured data"""
        report = data.get('Report', data)

        result = {
            'title': report.get('Header', {}).get('ReportName', 'Report'),
            'period': report.get('Header', {}).get('ReportBasis', ''),
            'currency': report.get('Header', {}).get('Currency', 'USD'),
            'sections': [],
            'totals': {}
        }

        # Parse rows
        for row in report.get('Rows', {}).get('Row', []):
            section = self._parse_report_row(row)
            if section:
                result['sections'].append(section)

        return result

    def _parse_report_row(self, row: Dict[str, Any], depth: int = 0) -> Optional[Dict[str, Any]]:
        """Recursively parse report row"""
        row_type = row.get('type', '')

        if row_type == 'Section':
            section = {
                'name': row.get('Header', {}).get('ColData', [{}])[0].get('value', ''),
                'rows': [],
                'summary': None
            }

            for sub_row in row.get('Rows', {}).get('Row', []):
                parsed = self._parse_report_row(sub_row, depth + 1)
                if parsed:
                    section['rows'].append(parsed)

            if 'Summary' in row:
                summary_data = row['Summary'].get('ColData', [])
                if len(summary_data) >= 2:
                    section['summary'] = {
                        'label': summary_data[0].get('value', ''),
                        'value': float(summary_data[1].get('value', 0) or 0)
                    }

            return section

        elif row_type == 'Data':
            col_data = row.get('ColData', [])
            if len(col_data) >= 2:
                return {
                    'label': col_data[0].get('value', ''),
                    'value': float(col_data[1].get('value', 0) or 0)
                }

        return None

    # ========== Cash Flow Analysis ==========

    def get_cash_flow_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive cash flow summary for analysis"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Fetch all relevant data
        invoices = self.get_invoices(start_date, end_date)
        bills = self.get_bills(start_date, end_date)
        transactions = self.get_bank_transactions(start_date=start_date, end_date=end_date)
        ar_aging = self.get_ar_aging()
        ap_aging = self.get_ap_aging()

        # Calculate summaries
        total_invoiced = sum(inv.amount for inv in invoices)
        total_collected = sum(inv.amount - inv.balance for inv in invoices)
        total_billed = sum(bill.amount for bill in bills)
        total_paid = sum(bill.amount - bill.balance for bill in bills)

        cash_in = sum(t.amount for t in transactions if t.amount > 0)
        cash_out = abs(sum(t.amount for t in transactions if t.amount < 0))

        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'accounts_receivable': {
                'total_invoiced': total_invoiced,
                'total_collected': total_collected,
                'collection_rate': (total_collected / total_invoiced * 100) if total_invoiced > 0 else 0,
                'outstanding': ar_aging['total'],
                'aging': ar_aging
            },
            'accounts_payable': {
                'total_billed': total_billed,
                'total_paid': total_paid,
                'payment_rate': (total_paid / total_billed * 100) if total_billed > 0 else 0,
                'outstanding': ap_aging['total'],
                'aging': ap_aging
            },
            'cash_flow': {
                'inflows': cash_in,
                'outflows': cash_out,
                'net_cash_flow': cash_in - cash_out
            },
            'metrics': {
                'days_sales_outstanding': self._calculate_dso(invoices),
                'days_payable_outstanding': self._calculate_dpo(bills),
                'cash_conversion_cycle': self._calculate_dso(invoices) - self._calculate_dpo(bills)
            }
        }

    def _calculate_dso(self, invoices: List[Invoice]) -> float:
        """Calculate Days Sales Outstanding"""
        if not invoices:
            return 0

        total_ar = sum(inv.balance for inv in invoices)
        avg_daily_sales = sum(inv.amount for inv in invoices) / 30  # Assume 30 day period

        if avg_daily_sales > 0:
            return total_ar / avg_daily_sales
        return 0

    def _calculate_dpo(self, bills: List[Bill]) -> float:
        """Calculate Days Payable Outstanding"""
        if not bills:
            return 0

        total_ap = sum(bill.balance for bill in bills)
        avg_daily_purchases = sum(bill.amount for bill in bills) / 30

        if avg_daily_purchases > 0:
            return total_ap / avg_daily_purchases
        return 0


# Demo mode for testing without real QuickBooks connection
class QuickBooksDemoClient(QuickBooksClient):
    """Demo client with mock data for testing"""

    def __init__(self):
        # Initialize with dummy config
        config = QuickBooksConfig(
            client_id='demo',
            client_secret='demo',
            redirect_uri='http://localhost:5101/demo'
        )
        super().__init__(config)
        self.token = QuickBooksToken(
            access_token='demo_token',
            refresh_token='demo_refresh',
            realm_id='demo_realm'
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Return mock data instead of making real API calls"""
        return self._get_demo_data(endpoint)

    def _get_demo_data(self, endpoint: str) -> Dict[str, Any]:
        """Generate realistic demo data"""
        from datetime import datetime, timedelta
        import random

        if 'Invoice' in endpoint:
            return self._demo_invoices()
        elif 'Bill' in endpoint:
            return self._demo_bills()
        elif 'Deposit' in endpoint:
            return self._demo_deposits()
        elif 'Purchase' in endpoint:
            return self._demo_purchases()
        elif 'ProfitAndLoss' in endpoint:
            return self._demo_pnl()
        elif 'BalanceSheet' in endpoint:
            return self._demo_balance_sheet()
        elif 'CashFlow' in endpoint:
            return self._demo_cash_flow()

        return {}

    def _demo_invoices(self) -> Dict[str, Any]:
        """Generate demo invoice data"""
        customers = ['Acme Corp', 'Tech Solutions', 'Global Industries', 'Summit Partners', 'Delta Services']
        invoices = []

        for i in range(20):
            days_ago = random.randint(0, 90)
            amount = random.uniform(1000, 50000)
            paid_pct = random.choice([0, 0, 0.5, 1.0, 1.0])

            invoices.append({
                'Id': str(1000 + i),
                'CustomerRef': {'name': random.choice(customers)},
                'TotalAmt': amount,
                'Balance': amount * (1 - paid_pct),
                'TxnDate': (datetime.utcnow() - timedelta(days=days_ago)).strftime('%Y-%m-%d'),
                'DueDate': (datetime.utcnow() - timedelta(days=days_ago - 30)).strftime('%Y-%m-%d'),
                'Line': []
            })

        return {'QueryResponse': {'Invoice': invoices}}

    def _demo_bills(self) -> Dict[str, Any]:
        """Generate demo bill data"""
        vendors = ['Office Supplies Co', 'Cloud Services Inc', 'Marketing Agency', 'Utilities Provider', 'Insurance Corp']
        bills = []

        for i in range(15):
            days_ago = random.randint(0, 60)
            amount = random.uniform(500, 20000)
            paid_pct = random.choice([0, 0, 0.5, 1.0, 1.0])

            bills.append({
                'Id': str(2000 + i),
                'VendorRef': {'name': random.choice(vendors)},
                'TotalAmt': amount,
                'Balance': amount * (1 - paid_pct),
                'TxnDate': (datetime.utcnow() - timedelta(days=days_ago)).strftime('%Y-%m-%d'),
                'DueDate': (datetime.utcnow() - timedelta(days=days_ago - 30)).strftime('%Y-%m-%d'),
                'Line': []
            })

        return {'QueryResponse': {'Bill': bills}}

    def _demo_deposits(self) -> Dict[str, Any]:
        """Generate demo deposit data"""
        deposits = []

        for i in range(10):
            days_ago = random.randint(0, 30)
            deposits.append({
                'Id': str(3000 + i),
                'TxnDate': (datetime.utcnow() - timedelta(days=days_ago)).strftime('%Y-%m-%d'),
                'TotalAmt': random.uniform(5000, 100000),
                'PrivateNote': 'Customer payment',
                'DepositToAccountRef': {'name': 'Operating Account'}
            })

        return {'QueryResponse': {'Deposit': deposits}}

    def _demo_purchases(self) -> Dict[str, Any]:
        """Generate demo purchase data"""
        purchases = []

        for i in range(15):
            days_ago = random.randint(0, 30)
            purchases.append({
                'Id': str(4000 + i),
                'TxnDate': (datetime.utcnow() - timedelta(days=days_ago)).strftime('%Y-%m-%d'),
                'TotalAmt': random.uniform(100, 10000),
                'PrivateNote': 'Operating expense',
                'AccountRef': {'name': 'Operating Account'},
                'EntityRef': {'name': 'Vendor'}
            })

        return {'QueryResponse': {'Purchase': purchases}}

    def _demo_pnl(self) -> Dict[str, Any]:
        """Generate demo P&L report"""
        return {
            'Report': {
                'Header': {'ReportName': 'Profit and Loss', 'Currency': 'USD'},
                'Rows': {'Row': [
                    {'type': 'Section', 'Header': {'ColData': [{'value': 'Income'}]},
                     'Rows': {'Row': [
                         {'type': 'Data', 'ColData': [{'value': 'Sales'}, {'value': '500000'}]},
                         {'type': 'Data', 'ColData': [{'value': 'Services'}, {'value': '150000'}]}
                     ]},
                     'Summary': {'ColData': [{'value': 'Total Income'}, {'value': '650000'}]}
                    },
                    {'type': 'Section', 'Header': {'ColData': [{'value': 'Expenses'}]},
                     'Rows': {'Row': [
                         {'type': 'Data', 'ColData': [{'value': 'Payroll'}, {'value': '200000'}]},
                         {'type': 'Data', 'ColData': [{'value': 'Rent'}, {'value': '50000'}]},
                         {'type': 'Data', 'ColData': [{'value': 'Utilities'}, {'value': '15000'}]}
                     ]},
                     'Summary': {'ColData': [{'value': 'Total Expenses'}, {'value': '265000'}]}
                    }
                ]}
            }
        }

    def _demo_balance_sheet(self) -> Dict[str, Any]:
        """Generate demo balance sheet"""
        return {
            'Report': {
                'Header': {'ReportName': 'Balance Sheet', 'Currency': 'USD'},
                'Rows': {'Row': [
                    {'type': 'Section', 'Header': {'ColData': [{'value': 'Assets'}]},
                     'Rows': {'Row': [
                         {'type': 'Data', 'ColData': [{'value': 'Cash'}, {'value': '250000'}]},
                         {'type': 'Data', 'ColData': [{'value': 'Accounts Receivable'}, {'value': '180000'}]}
                     ]},
                     'Summary': {'ColData': [{'value': 'Total Assets'}, {'value': '430000'}]}
                    }
                ]}
            }
        }

    def _demo_cash_flow(self) -> Dict[str, Any]:
        """Generate demo cash flow statement"""
        return {
            'Report': {
                'Header': {'ReportName': 'Cash Flow Statement', 'Currency': 'USD'},
                'Rows': {'Row': [
                    {'type': 'Section', 'Header': {'ColData': [{'value': 'Operating Activities'}]},
                     'Summary': {'ColData': [{'value': 'Net Cash from Operations'}, {'value': '125000'}]}
                    }
                ]}
            }
        }
