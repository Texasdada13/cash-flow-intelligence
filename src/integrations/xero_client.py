"""
Xero Accounting Integration Client

Provides OAuth2 authentication and data fetching for:
- Invoices (Accounts Receivable)
- Bills (Accounts Payable)
- Bank Transactions
- Profit & Loss Reports
- Balance Sheet
- Cash Flow Analysis
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
import base64

logger = logging.getLogger(__name__)


@dataclass
class XeroConfig:
    """Configuration for Xero OAuth and API access"""
    client_id: str
    client_secret: str
    redirect_uri: str

    @property
    def auth_url(self) -> str:
        return "https://login.xero.com/identity/connect/authorize"

    @property
    def token_url(self) -> str:
        return "https://identity.xero.com/connect/token"

    @property
    def api_base_url(self) -> str:
        return "https://api.xero.com/api.xro/2.0"

    @classmethod
    def from_env(cls) -> 'XeroConfig':
        """Create config from environment variables"""
        return cls(
            client_id=os.getenv('XERO_CLIENT_ID', ''),
            client_secret=os.getenv('XERO_CLIENT_SECRET', ''),
            redirect_uri=os.getenv('XERO_REDIRECT_URI', 'http://localhost:5101/integrations/xero/callback')
        )


@dataclass
class XeroToken:
    """OAuth token storage"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 1800
    created_at: datetime = field(default_factory=datetime.utcnow)
    tenant_id: str = ""

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
            'tenant_id': self.tenant_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'XeroToken':
        return cls(
            access_token=data['access_token'],
            refresh_token=data['refresh_token'],
            token_type=data.get('token_type', 'Bearer'),
            expires_in=data.get('expires_in', 1800),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.utcnow(),
            tenant_id=data.get('tenant_id', '')
        )


@dataclass
class XeroInvoice:
    """Xero Invoice representation"""
    id: str
    invoice_number: str
    contact_name: str
    amount_due: float
    amount_paid: float
    total: float
    due_date: Optional[datetime]
    date: datetime
    status: str  # PAID, AUTHORISED, DRAFT, VOIDED
    line_items: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_overdue(self) -> bool:
        if self.due_date and self.amount_due > 0:
            return datetime.utcnow() > self.due_date
        return False


@dataclass
class XeroBill:
    """Xero Bill (AP) representation"""
    id: str
    invoice_number: str
    contact_name: str
    amount_due: float
    amount_paid: float
    total: float
    due_date: Optional[datetime]
    date: datetime
    status: str
    line_items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class XeroBankTransaction:
    """Xero bank transaction representation"""
    id: str
    date: datetime
    amount: float
    reference: str
    contact_name: Optional[str]
    bank_account: str
    transaction_type: str  # RECEIVE, SPEND
    is_reconciled: bool = False


class XeroClient:
    """
    Xero Accounting API Client

    Handles OAuth2 authentication and provides methods for fetching
    financial data relevant to cash flow analysis.
    """

    def __init__(self, config: XeroConfig):
        self.config = config
        self.token: Optional[XeroToken] = None
        self._session = requests.Session()

    # ========== OAuth Methods ==========

    def get_authorization_url(self, state: str = "") -> str:
        """Generate OAuth authorization URL for user consent"""
        params = {
            'response_type': 'code',
            'client_id': self.config.client_id,
            'redirect_uri': self.config.redirect_uri,
            'scope': 'openid profile email accounting.transactions accounting.reports.read accounting.contacts.read offline_access',
            'state': state
        }
        return f"{self.config.auth_url}?{urlencode(params)}"

    def exchange_code_for_token(self, authorization_code: str) -> XeroToken:
        """Exchange authorization code for access token"""
        auth_header = base64.b64encode(
            f"{self.config.client_id}:{self.config.client_secret}".encode()
        ).decode()

        response = self._session.post(
            self.config.token_url,
            headers={
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={
                'grant_type': 'authorization_code',
                'code': authorization_code,
                'redirect_uri': self.config.redirect_uri
            }
        )
        response.raise_for_status()
        data = response.json()

        self.token = XeroToken(
            access_token=data['access_token'],
            refresh_token=data['refresh_token'],
            token_type=data.get('token_type', 'Bearer'),
            expires_in=data.get('expires_in', 1800)
        )

        # Get tenant ID
        self._fetch_tenant_id()

        return self.token

    def _fetch_tenant_id(self):
        """Fetch the tenant (organization) ID"""
        response = self._session.get(
            'https://api.xero.com/connections',
            headers={'Authorization': f'Bearer {self.token.access_token}'}
        )
        response.raise_for_status()
        connections = response.json()

        if connections:
            self.token.tenant_id = connections[0]['tenantId']

    def refresh_access_token(self) -> XeroToken:
        """Refresh the access token using refresh token"""
        if not self.token:
            raise ValueError("No token available to refresh")

        auth_header = base64.b64encode(
            f"{self.config.client_id}:{self.config.client_secret}".encode()
        ).decode()

        response = self._session.post(
            self.config.token_url,
            headers={
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={
                'grant_type': 'refresh_token',
                'refresh_token': self.token.refresh_token
            }
        )
        response.raise_for_status()
        data = response.json()

        self.token = XeroToken(
            access_token=data['access_token'],
            refresh_token=data.get('refresh_token', self.token.refresh_token),
            token_type=data.get('token_type', 'Bearer'),
            expires_in=data.get('expires_in', 1800),
            tenant_id=self.token.tenant_id
        )
        return self.token

    def set_token(self, token: XeroToken):
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

        url = f"{self.config.api_base_url}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.token.access_token}',
            'xero-tenant-id': self.token.tenant_id,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        response = self._session.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    # ========== Invoice (AR) Methods ==========

    def get_invoices(self, start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None,
                     status: Optional[str] = None) -> List[XeroInvoice]:
        """Fetch sales invoices (Accounts Receivable)"""
        params = {'where': 'Type=="ACCREC"'}

        if status:
            params['where'] += f' AND Status=="{status}"'

        data = self._make_request('GET', 'Invoices', params=params)
        invoices = []

        for inv in data.get('Invoices', []):
            due_date = None
            if inv.get('DueDateString'):
                due_date = datetime.fromisoformat(inv['DueDateString'].replace('Z', '+00:00'))

            invoice = XeroInvoice(
                id=inv['InvoiceID'],
                invoice_number=inv.get('InvoiceNumber', ''),
                contact_name=inv.get('Contact', {}).get('Name', 'Unknown'),
                amount_due=float(inv.get('AmountDue', 0)),
                amount_paid=float(inv.get('AmountPaid', 0)),
                total=float(inv.get('Total', 0)),
                due_date=due_date,
                date=datetime.fromisoformat(inv['DateString'].replace('Z', '+00:00')) if inv.get('DateString') else datetime.utcnow(),
                status=inv.get('Status', 'DRAFT'),
                line_items=inv.get('LineItems', [])
            )
            invoices.append(invoice)

        return invoices

    def get_ar_aging(self) -> Dict[str, Any]:
        """Get Accounts Receivable aging summary"""
        data = self._make_request('GET', 'Reports/AgedReceivablesByContact')

        aging = {
            'current': 0,
            '1_30_days': 0,
            '31_60_days': 0,
            '61_90_days': 0,
            'over_90_days': 0,
            'total': 0
        }

        # Parse the report rows
        for row in data.get('Reports', [{}])[0].get('Rows', []):
            if row.get('RowType') == 'Section':
                for cell_row in row.get('Rows', []):
                    if cell_row.get('RowType') == 'Row':
                        cells = cell_row.get('Cells', [])
                        if len(cells) >= 6:
                            aging['current'] += float(cells[1].get('Value', 0) or 0)
                            aging['1_30_days'] += float(cells[2].get('Value', 0) or 0)
                            aging['31_60_days'] += float(cells[3].get('Value', 0) or 0)
                            aging['61_90_days'] += float(cells[4].get('Value', 0) or 0)
                            aging['over_90_days'] += float(cells[5].get('Value', 0) or 0)

        aging['total'] = sum([aging['current'], aging['1_30_days'], aging['31_60_days'],
                             aging['61_90_days'], aging['over_90_days']])
        return aging

    # ========== Bill (AP) Methods ==========

    def get_bills(self, start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> List[XeroBill]:
        """Fetch bills (Accounts Payable)"""
        params = {'where': 'Type=="ACCPAY"'}

        data = self._make_request('GET', 'Invoices', params=params)
        bills = []

        for bill_data in data.get('Invoices', []):
            due_date = None
            if bill_data.get('DueDateString'):
                due_date = datetime.fromisoformat(bill_data['DueDateString'].replace('Z', '+00:00'))

            bill = XeroBill(
                id=bill_data['InvoiceID'],
                invoice_number=bill_data.get('InvoiceNumber', ''),
                contact_name=bill_data.get('Contact', {}).get('Name', 'Unknown'),
                amount_due=float(bill_data.get('AmountDue', 0)),
                amount_paid=float(bill_data.get('AmountPaid', 0)),
                total=float(bill_data.get('Total', 0)),
                due_date=due_date,
                date=datetime.fromisoformat(bill_data['DateString'].replace('Z', '+00:00')) if bill_data.get('DateString') else datetime.utcnow(),
                status=bill_data.get('Status', 'DRAFT'),
                line_items=bill_data.get('LineItems', [])
            )
            bills.append(bill)

        return bills

    def get_ap_aging(self) -> Dict[str, Any]:
        """Get Accounts Payable aging summary"""
        data = self._make_request('GET', 'Reports/AgedPayablesByContact')

        aging = {
            'current': 0,
            '1_30_days': 0,
            '31_60_days': 0,
            '61_90_days': 0,
            'over_90_days': 0,
            'total': 0
        }

        # Parse the report rows
        for row in data.get('Reports', [{}])[0].get('Rows', []):
            if row.get('RowType') == 'Section':
                for cell_row in row.get('Rows', []):
                    if cell_row.get('RowType') == 'Row':
                        cells = cell_row.get('Cells', [])
                        if len(cells) >= 6:
                            aging['current'] += float(cells[1].get('Value', 0) or 0)
                            aging['1_30_days'] += float(cells[2].get('Value', 0) or 0)
                            aging['31_60_days'] += float(cells[3].get('Value', 0) or 0)
                            aging['61_90_days'] += float(cells[4].get('Value', 0) or 0)
                            aging['over_90_days'] += float(cells[5].get('Value', 0) or 0)

        aging['total'] = sum([aging['current'], aging['1_30_days'], aging['31_60_days'],
                             aging['61_90_days'], aging['over_90_days']])
        return aging

    # ========== Bank Transactions ==========

    def get_bank_transactions(self, start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> List[XeroBankTransaction]:
        """Fetch bank transactions"""
        params = {}
        if start_date:
            params['where'] = f'Date >= DateTime({start_date.year}, {start_date.month}, {start_date.day})'

        data = self._make_request('GET', 'BankTransactions', params=params)
        transactions = []

        for txn in data.get('BankTransactions', []):
            transactions.append(XeroBankTransaction(
                id=txn['BankTransactionID'],
                date=datetime.fromisoformat(txn['DateString'].replace('Z', '+00:00')) if txn.get('DateString') else datetime.utcnow(),
                amount=float(txn.get('Total', 0)) if txn.get('Type') == 'RECEIVE' else -float(txn.get('Total', 0)),
                reference=txn.get('Reference', ''),
                contact_name=txn.get('Contact', {}).get('Name'),
                bank_account=txn.get('BankAccount', {}).get('Name', 'Unknown'),
                transaction_type=txn.get('Type', 'SPEND'),
                is_reconciled=txn.get('IsReconciled', False)
            ))

        return transactions

    # ========== Reports ==========

    def get_profit_and_loss(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Fetch Profit & Loss report"""
        params = {
            'fromDate': start_date.strftime('%Y-%m-%d'),
            'toDate': end_date.strftime('%Y-%m-%d')
        }

        data = self._make_request('GET', 'Reports/ProfitAndLoss', params=params)
        return self._parse_report(data)

    def get_balance_sheet(self, as_of_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Fetch Balance Sheet report"""
        params = {}
        if as_of_date:
            params['date'] = as_of_date.strftime('%Y-%m-%d')

        data = self._make_request('GET', 'Reports/BalanceSheet', params=params)
        return self._parse_report(data)

    def _parse_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Xero report format into structured data"""
        reports = data.get('Reports', [])
        if not reports:
            return {'sections': [], 'totals': {}}

        report = reports[0]
        result = {
            'title': report.get('ReportName', 'Report'),
            'period': f"{report.get('ReportDate', '')}",
            'sections': [],
            'totals': {}
        }

        for row in report.get('Rows', []):
            section = self._parse_report_row(row)
            if section:
                result['sections'].append(section)

        return result

    def _parse_report_row(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse report row"""
        row_type = row.get('RowType', '')

        if row_type == 'Section':
            section = {
                'name': row.get('Title', ''),
                'rows': [],
                'summary': None
            }

            for sub_row in row.get('Rows', []):
                if sub_row.get('RowType') == 'Row':
                    cells = sub_row.get('Cells', [])
                    if len(cells) >= 2:
                        section['rows'].append({
                            'label': cells[0].get('Value', ''),
                            'value': float(cells[1].get('Value', 0) or 0)
                        })
                elif sub_row.get('RowType') == 'SummaryRow':
                    cells = sub_row.get('Cells', [])
                    if len(cells) >= 2:
                        section['summary'] = {
                            'label': cells[0].get('Value', ''),
                            'value': float(cells[1].get('Value', 0) or 0)
                        }

            return section

        return None

    # ========== Cash Flow Analysis ==========

    def get_cash_flow_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive cash flow summary for analysis"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Fetch all relevant data
        invoices = self.get_invoices()
        bills = self.get_bills()
        transactions = self.get_bank_transactions(start_date=start_date)
        ar_aging = self.get_ar_aging()
        ap_aging = self.get_ap_aging()

        # Filter by date range
        invoices = [i for i in invoices if start_date <= i.date <= end_date]
        bills = [b for b in bills if start_date <= b.date <= end_date]

        # Calculate summaries
        total_invoiced = sum(inv.total for inv in invoices)
        total_collected = sum(inv.amount_paid for inv in invoices)
        total_billed = sum(bill.total for bill in bills)
        total_paid = sum(bill.amount_paid for bill in bills)

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
                'days_payable_outstanding': self._calculate_dpo(bills)
            }
        }

    def _calculate_dso(self, invoices: List[XeroInvoice]) -> float:
        """Calculate Days Sales Outstanding"""
        if not invoices:
            return 0

        total_ar = sum(inv.amount_due for inv in invoices)
        avg_daily_sales = sum(inv.total for inv in invoices) / 30

        if avg_daily_sales > 0:
            return total_ar / avg_daily_sales
        return 0

    def _calculate_dpo(self, bills: List[XeroBill]) -> float:
        """Calculate Days Payable Outstanding"""
        if not bills:
            return 0

        total_ap = sum(bill.amount_due for bill in bills)
        avg_daily_purchases = sum(bill.total for bill in bills) / 30

        if avg_daily_purchases > 0:
            return total_ap / avg_daily_purchases
        return 0


# Demo mode for testing without real Xero connection
class XeroDemoClient(XeroClient):
    """Demo client with mock data for testing"""

    def __init__(self):
        config = XeroConfig(
            client_id='demo',
            client_secret='demo',
            redirect_uri='http://localhost:5101/demo'
        )
        super().__init__(config)
        self.token = XeroToken(
            access_token='demo_token',
            refresh_token='demo_refresh',
            tenant_id='demo_tenant'
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Return mock data instead of making real API calls"""
        return self._get_demo_data(endpoint)

    def _get_demo_data(self, endpoint: str) -> Dict[str, Any]:
        """Generate realistic demo data"""
        import random

        if 'Invoices' in endpoint:
            return self._demo_invoices()
        elif 'BankTransactions' in endpoint:
            return self._demo_bank_transactions()
        elif 'AgedReceivables' in endpoint:
            return self._demo_ar_aging()
        elif 'AgedPayables' in endpoint:
            return self._demo_ap_aging()
        elif 'ProfitAndLoss' in endpoint:
            return self._demo_pnl()
        elif 'BalanceSheet' in endpoint:
            return self._demo_balance_sheet()

        return {}

    def _demo_invoices(self) -> Dict[str, Any]:
        """Generate demo invoice data"""
        import random

        contacts = ['ABC Company', 'XYZ Ltd', 'Tech Corp', 'Global Services', 'Local Business']
        invoices = []

        for i in range(25):
            days_ago = random.randint(0, 90)
            total = random.uniform(1000, 75000)
            paid_pct = random.choice([0, 0.3, 0.5, 1.0, 1.0])

            invoices.append({
                'InvoiceID': f'inv-{1000 + i}',
                'InvoiceNumber': f'INV-{1000 + i}',
                'Contact': {'Name': random.choice(contacts)},
                'Total': total,
                'AmountPaid': total * paid_pct,
                'AmountDue': total * (1 - paid_pct),
                'DateString': (datetime.utcnow() - timedelta(days=days_ago)).isoformat(),
                'DueDateString': (datetime.utcnow() - timedelta(days=days_ago - 30)).isoformat(),
                'Status': 'PAID' if paid_pct == 1.0 else 'AUTHORISED',
                'Type': 'ACCREC',
                'LineItems': []
            })

        return {'Invoices': invoices}

    def _demo_bank_transactions(self) -> Dict[str, Any]:
        """Generate demo bank transactions"""
        import random

        transactions = []

        for i in range(30):
            days_ago = random.randint(0, 30)
            is_receive = random.choice([True, False])

            transactions.append({
                'BankTransactionID': f'txn-{3000 + i}',
                'DateString': (datetime.utcnow() - timedelta(days=days_ago)).isoformat(),
                'Total': random.uniform(500, 50000),
                'Reference': f'TXN-{3000 + i}',
                'Contact': {'Name': 'Contact' if random.random() > 0.3 else None},
                'BankAccount': {'Name': 'Operating Account'},
                'Type': 'RECEIVE' if is_receive else 'SPEND',
                'IsReconciled': random.choice([True, False])
            })

        return {'BankTransactions': transactions}

    def _demo_ar_aging(self) -> Dict[str, Any]:
        """Generate demo AR aging report"""
        return {
            'Reports': [{
                'Rows': [{
                    'RowType': 'Section',
                    'Rows': [
                        {'RowType': 'Row', 'Cells': [
                            {'Value': 'Customer 1'},
                            {'Value': '15000'},
                            {'Value': '8000'},
                            {'Value': '3000'},
                            {'Value': '2000'},
                            {'Value': '1000'}
                        ]},
                        {'RowType': 'Row', 'Cells': [
                            {'Value': 'Customer 2'},
                            {'Value': '25000'},
                            {'Value': '12000'},
                            {'Value': '5000'},
                            {'Value': '0'},
                            {'Value': '0'}
                        ]}
                    ]
                }]
            }]
        }

    def _demo_ap_aging(self) -> Dict[str, Any]:
        """Generate demo AP aging report"""
        return {
            'Reports': [{
                'Rows': [{
                    'RowType': 'Section',
                    'Rows': [
                        {'RowType': 'Row', 'Cells': [
                            {'Value': 'Vendor 1'},
                            {'Value': '10000'},
                            {'Value': '5000'},
                            {'Value': '2000'},
                            {'Value': '1000'},
                            {'Value': '500'}
                        ]}
                    ]
                }]
            }]
        }

    def _demo_pnl(self) -> Dict[str, Any]:
        """Generate demo P&L report"""
        return {
            'Reports': [{
                'ReportName': 'Profit and Loss',
                'Rows': [
                    {
                        'RowType': 'Section',
                        'Title': 'Revenue',
                        'Rows': [
                            {'RowType': 'Row', 'Cells': [{'Value': 'Sales'}, {'Value': '450000'}]},
                            {'RowType': 'SummaryRow', 'Cells': [{'Value': 'Total Revenue'}, {'Value': '450000'}]}
                        ]
                    },
                    {
                        'RowType': 'Section',
                        'Title': 'Expenses',
                        'Rows': [
                            {'RowType': 'Row', 'Cells': [{'Value': 'Operating Expenses'}, {'Value': '180000'}]},
                            {'RowType': 'SummaryRow', 'Cells': [{'Value': 'Total Expenses'}, {'Value': '180000'}]}
                        ]
                    }
                ]
            }]
        }

    def _demo_balance_sheet(self) -> Dict[str, Any]:
        """Generate demo balance sheet"""
        return {
            'Reports': [{
                'ReportName': 'Balance Sheet',
                'Rows': [
                    {
                        'RowType': 'Section',
                        'Title': 'Assets',
                        'Rows': [
                            {'RowType': 'Row', 'Cells': [{'Value': 'Bank'}, {'Value': '320000'}]},
                            {'RowType': 'Row', 'Cells': [{'Value': 'Accounts Receivable'}, {'Value': '145000'}]},
                            {'RowType': 'SummaryRow', 'Cells': [{'Value': 'Total Assets'}, {'Value': '465000'}]}
                        ]
                    }
                ]
            }]
        }
