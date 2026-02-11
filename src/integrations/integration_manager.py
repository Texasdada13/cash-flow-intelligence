"""
Integration Manager for Cash Flow Intelligence

Provides a unified interface for managing multiple accounting integrations.
Supports QuickBooks Online and Xero with consistent data formats.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .quickbooks_client import (
    QuickBooksClient, QuickBooksConfig, QuickBooksToken,
    QuickBooksDemoClient, Invoice, Bill, BankTransaction
)
from .xero_client import (
    XeroClient, XeroConfig, XeroToken,
    XeroDemoClient, XeroInvoice, XeroBill, XeroBankTransaction
)

logger = logging.getLogger(__name__)


class IntegrationType(Enum):
    QUICKBOOKS = "quickbooks"
    XERO = "xero"
    DEMO = "demo"


@dataclass
class IntegrationStatus:
    """Status of an integration connection"""
    integration_type: IntegrationType
    is_connected: bool
    last_sync: Optional[datetime] = None
    company_name: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class UnifiedInvoice:
    """Unified invoice format across integrations"""
    id: str
    source: IntegrationType
    customer_name: str
    invoice_number: str
    total_amount: float
    amount_due: float
    amount_paid: float
    issue_date: datetime
    due_date: Optional[datetime]
    status: str  # Open, Paid, Overdue, Draft
    days_outstanding: int = 0

    @classmethod
    def from_quickbooks(cls, inv: Invoice) -> 'UnifiedInvoice':
        return cls(
            id=inv.id,
            source=IntegrationType.QUICKBOOKS,
            customer_name=inv.customer_name,
            invoice_number=inv.id,
            total_amount=inv.amount,
            amount_due=inv.balance,
            amount_paid=inv.amount - inv.balance,
            issue_date=inv.create_date,
            due_date=inv.due_date,
            status=inv.status,
            days_outstanding=inv.days_outstanding
        )

    @classmethod
    def from_xero(cls, inv: XeroInvoice) -> 'UnifiedInvoice':
        return cls(
            id=inv.id,
            source=IntegrationType.XERO,
            customer_name=inv.contact_name,
            invoice_number=inv.invoice_number,
            total_amount=inv.total,
            amount_due=inv.amount_due,
            amount_paid=inv.amount_paid,
            issue_date=inv.date,
            due_date=inv.due_date,
            status='Overdue' if inv.is_overdue else inv.status,
            days_outstanding=(datetime.utcnow() - inv.date).days
        )


@dataclass
class UnifiedBill:
    """Unified bill format across integrations"""
    id: str
    source: IntegrationType
    vendor_name: str
    bill_number: str
    total_amount: float
    amount_due: float
    amount_paid: float
    issue_date: datetime
    due_date: Optional[datetime]
    status: str

    @classmethod
    def from_quickbooks(cls, bill: Bill) -> 'UnifiedBill':
        return cls(
            id=bill.id,
            source=IntegrationType.QUICKBOOKS,
            vendor_name=bill.vendor_name,
            bill_number=bill.id,
            total_amount=bill.amount,
            amount_due=bill.balance,
            amount_paid=bill.amount - bill.balance,
            issue_date=bill.create_date,
            due_date=bill.due_date,
            status=bill.status
        )

    @classmethod
    def from_xero(cls, bill: XeroBill) -> 'UnifiedBill':
        return cls(
            id=bill.id,
            source=IntegrationType.XERO,
            vendor_name=bill.contact_name,
            bill_number=bill.invoice_number,
            total_amount=bill.total,
            amount_due=bill.amount_due,
            amount_paid=bill.amount_paid,
            issue_date=bill.date,
            due_date=bill.due_date,
            status=bill.status
        )


@dataclass
class UnifiedTransaction:
    """Unified transaction format across integrations"""
    id: str
    source: IntegrationType
    date: datetime
    amount: float
    description: str
    account_name: str
    transaction_type: str  # Inflow, Outflow
    category: Optional[str] = None

    @classmethod
    def from_quickbooks(cls, txn: BankTransaction) -> 'UnifiedTransaction':
        return cls(
            id=txn.id,
            source=IntegrationType.QUICKBOOKS,
            date=txn.date,
            amount=txn.amount,
            description=txn.description,
            account_name=txn.account_name,
            transaction_type='Inflow' if txn.amount > 0 else 'Outflow',
            category=txn.category
        )

    @classmethod
    def from_xero(cls, txn: XeroBankTransaction) -> 'UnifiedTransaction':
        return cls(
            id=txn.id,
            source=IntegrationType.XERO,
            date=txn.date,
            amount=txn.amount,
            description=txn.reference,
            account_name=txn.bank_account,
            transaction_type='Inflow' if txn.amount > 0 else 'Outflow'
        )


class IntegrationManager:
    """
    Manages accounting integrations for Cash Flow Intelligence.

    Provides a unified interface for:
    - OAuth authentication flows
    - Data fetching from multiple sources
    - Normalized data formats
    - Token storage and refresh
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), '..', '..', 'instance', 'integrations'
        )
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)

        self._quickbooks_client: Optional[QuickBooksClient] = None
        self._xero_client: Optional[XeroClient] = None
        self._demo_mode = False

    # ========== Configuration ==========

    def configure_quickbooks(self, config: Optional[QuickBooksConfig] = None):
        """Configure QuickBooks integration"""
        config = config or QuickBooksConfig.from_env()
        self._quickbooks_client = QuickBooksClient(config)
        self._load_stored_token(IntegrationType.QUICKBOOKS)

    def configure_xero(self, config: Optional[XeroConfig] = None):
        """Configure Xero integration"""
        config = config or XeroConfig.from_env()
        self._xero_client = XeroClient(config)
        self._load_stored_token(IntegrationType.XERO)

    def enable_demo_mode(self):
        """Enable demo mode with mock data"""
        self._demo_mode = True
        self._quickbooks_client = QuickBooksDemoClient()
        self._xero_client = XeroDemoClient()

    # ========== OAuth Authentication ==========

    def get_auth_url(self, integration_type: IntegrationType, state: str = "") -> str:
        """Get OAuth authorization URL for an integration"""
        if integration_type == IntegrationType.QUICKBOOKS:
            if not self._quickbooks_client:
                self.configure_quickbooks()
            return self._quickbooks_client.get_authorization_url(state)
        elif integration_type == IntegrationType.XERO:
            if not self._xero_client:
                self.configure_xero()
            return self._xero_client.get_authorization_url(state)
        else:
            raise ValueError(f"Unsupported integration type: {integration_type}")

    def handle_oauth_callback(self, integration_type: IntegrationType,
                               authorization_code: str,
                               realm_id: str = "") -> bool:
        """Handle OAuth callback and exchange code for tokens"""
        try:
            if integration_type == IntegrationType.QUICKBOOKS:
                if not self._quickbooks_client:
                    self.configure_quickbooks()
                token = self._quickbooks_client.exchange_code_for_token(authorization_code, realm_id)
                self._store_token(IntegrationType.QUICKBOOKS, token.to_dict())
                return True

            elif integration_type == IntegrationType.XERO:
                if not self._xero_client:
                    self.configure_xero()
                token = self._xero_client.exchange_code_for_token(authorization_code)
                self._store_token(IntegrationType.XERO, token.to_dict())
                return True

        except Exception as e:
            logger.error(f"OAuth callback failed for {integration_type}: {e}")
            return False

        return False

    def disconnect(self, integration_type: IntegrationType):
        """Disconnect an integration and remove stored tokens"""
        token_file = self._get_token_path(integration_type)
        if os.path.exists(token_file):
            os.remove(token_file)

        if integration_type == IntegrationType.QUICKBOOKS:
            self._quickbooks_client = None
        elif integration_type == IntegrationType.XERO:
            self._xero_client = None

    # ========== Status ==========

    def get_status(self, integration_type: IntegrationType) -> IntegrationStatus:
        """Get the status of an integration"""
        is_connected = False
        last_sync = None
        company_name = None
        error_message = None

        try:
            if integration_type == IntegrationType.QUICKBOOKS and self._quickbooks_client:
                if self._quickbooks_client.token:
                    is_connected = True
                    # Try a simple API call to verify connection
                    try:
                        self._quickbooks_client.get_invoices()
                    except Exception as e:
                        is_connected = False
                        error_message = str(e)

            elif integration_type == IntegrationType.XERO and self._xero_client:
                if self._xero_client.token:
                    is_connected = True
                    try:
                        self._xero_client.get_invoices()
                    except Exception as e:
                        is_connected = False
                        error_message = str(e)

            elif integration_type == IntegrationType.DEMO:
                is_connected = self._demo_mode
                company_name = "Demo Company"

        except Exception as e:
            error_message = str(e)

        return IntegrationStatus(
            integration_type=integration_type,
            is_connected=is_connected,
            last_sync=last_sync,
            company_name=company_name,
            error_message=error_message
        )

    def get_all_statuses(self) -> List[IntegrationStatus]:
        """Get status for all configured integrations"""
        statuses = []

        if self._quickbooks_client:
            statuses.append(self.get_status(IntegrationType.QUICKBOOKS))
        if self._xero_client:
            statuses.append(self.get_status(IntegrationType.XERO))
        if self._demo_mode:
            statuses.append(self.get_status(IntegrationType.DEMO))

        return statuses

    # ========== Unified Data Access ==========

    def get_invoices(self, source: Optional[IntegrationType] = None,
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None) -> List[UnifiedInvoice]:
        """Get invoices from all connected integrations or a specific one"""
        invoices = []

        if source is None or source == IntegrationType.QUICKBOOKS:
            if self._quickbooks_client and self._quickbooks_client.token:
                try:
                    qb_invoices = self._quickbooks_client.get_invoices(start_date, end_date)
                    invoices.extend([UnifiedInvoice.from_quickbooks(inv) for inv in qb_invoices])
                except Exception as e:
                    logger.error(f"Failed to fetch QuickBooks invoices: {e}")

        if source is None or source == IntegrationType.XERO:
            if self._xero_client and self._xero_client.token:
                try:
                    xero_invoices = self._xero_client.get_invoices(start_date, end_date)
                    invoices.extend([UnifiedInvoice.from_xero(inv) for inv in xero_invoices])
                except Exception as e:
                    logger.error(f"Failed to fetch Xero invoices: {e}")

        return invoices

    def get_bills(self, source: Optional[IntegrationType] = None,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> List[UnifiedBill]:
        """Get bills from all connected integrations or a specific one"""
        bills = []

        if source is None or source == IntegrationType.QUICKBOOKS:
            if self._quickbooks_client and self._quickbooks_client.token:
                try:
                    qb_bills = self._quickbooks_client.get_bills(start_date, end_date)
                    bills.extend([UnifiedBill.from_quickbooks(b) for b in qb_bills])
                except Exception as e:
                    logger.error(f"Failed to fetch QuickBooks bills: {e}")

        if source is None or source == IntegrationType.XERO:
            if self._xero_client and self._xero_client.token:
                try:
                    xero_bills = self._xero_client.get_bills(start_date, end_date)
                    bills.extend([UnifiedBill.from_xero(b) for b in xero_bills])
                except Exception as e:
                    logger.error(f"Failed to fetch Xero bills: {e}")

        return bills

    def get_transactions(self, source: Optional[IntegrationType] = None,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> List[UnifiedTransaction]:
        """Get bank transactions from all connected integrations"""
        transactions = []

        if source is None or source == IntegrationType.QUICKBOOKS:
            if self._quickbooks_client and self._quickbooks_client.token:
                try:
                    qb_txns = self._quickbooks_client.get_bank_transactions(
                        start_date=start_date, end_date=end_date
                    )
                    transactions.extend([UnifiedTransaction.from_quickbooks(t) for t in qb_txns])
                except Exception as e:
                    logger.error(f"Failed to fetch QuickBooks transactions: {e}")

        if source is None or source == IntegrationType.XERO:
            if self._xero_client and self._xero_client.token:
                try:
                    xero_txns = self._xero_client.get_bank_transactions(
                        start_date=start_date, end_date=end_date
                    )
                    transactions.extend([UnifiedTransaction.from_xero(t) for t in xero_txns])
                except Exception as e:
                    logger.error(f"Failed to fetch Xero transactions: {e}")

        return sorted(transactions, key=lambda t: t.date, reverse=True)

    def get_ar_aging(self, source: Optional[IntegrationType] = None) -> Dict[str, Any]:
        """Get combined AR aging report"""
        aging = {
            'current': 0,
            '1_30_days': 0,
            '31_60_days': 0,
            '61_90_days': 0,
            'over_90_days': 0,
            'total': 0,
            'sources': []
        }

        if source is None or source == IntegrationType.QUICKBOOKS:
            if self._quickbooks_client and self._quickbooks_client.token:
                try:
                    qb_aging = self._quickbooks_client.get_ar_aging()
                    for key in ['current', '1_30_days', '31_60_days', '61_90_days', 'over_90_days', 'total']:
                        aging[key] += qb_aging.get(key, 0)
                    aging['sources'].append({'type': 'QuickBooks', 'data': qb_aging})
                except Exception as e:
                    logger.error(f"Failed to fetch QuickBooks AR aging: {e}")

        if source is None or source == IntegrationType.XERO:
            if self._xero_client and self._xero_client.token:
                try:
                    xero_aging = self._xero_client.get_ar_aging()
                    for key in ['current', '1_30_days', '31_60_days', '61_90_days', 'over_90_days', 'total']:
                        aging[key] += xero_aging.get(key, 0)
                    aging['sources'].append({'type': 'Xero', 'data': xero_aging})
                except Exception as e:
                    logger.error(f"Failed to fetch Xero AR aging: {e}")

        return aging

    def get_ap_aging(self, source: Optional[IntegrationType] = None) -> Dict[str, Any]:
        """Get combined AP aging report"""
        aging = {
            'current': 0,
            '1_30_days': 0,
            '31_60_days': 0,
            '61_90_days': 0,
            'over_90_days': 0,
            'total': 0,
            'sources': []
        }

        if source is None or source == IntegrationType.QUICKBOOKS:
            if self._quickbooks_client and self._quickbooks_client.token:
                try:
                    qb_aging = self._quickbooks_client.get_ap_aging()
                    for key in ['current', '1_30_days', '31_60_days', '61_90_days', 'over_90_days', 'total']:
                        aging[key] += qb_aging.get(key, 0)
                    aging['sources'].append({'type': 'QuickBooks', 'data': qb_aging})
                except Exception as e:
                    logger.error(f"Failed to fetch QuickBooks AP aging: {e}")

        if source is None or source == IntegrationType.XERO:
            if self._xero_client and self._xero_client.token:
                try:
                    xero_aging = self._xero_client.get_ap_aging()
                    for key in ['current', '1_30_days', '31_60_days', '61_90_days', 'over_90_days', 'total']:
                        aging[key] += xero_aging.get(key, 0)
                    aging['sources'].append({'type': 'Xero', 'data': xero_aging})
                except Exception as e:
                    logger.error(f"Failed to fetch Xero AP aging: {e}")

        return aging

    # ========== Cash Flow Summary ==========

    def get_unified_cash_flow_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive cash flow summary from all connected integrations"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Fetch unified data
        invoices = self.get_invoices(start_date=start_date, end_date=end_date)
        bills = self.get_bills(start_date=start_date, end_date=end_date)
        transactions = self.get_transactions(start_date=start_date, end_date=end_date)
        ar_aging = self.get_ar_aging()
        ap_aging = self.get_ap_aging()

        # Calculate metrics
        total_invoiced = sum(inv.total_amount for inv in invoices)
        total_collected = sum(inv.amount_paid for inv in invoices)
        total_billed = sum(bill.total_amount for bill in bills)
        total_paid = sum(bill.amount_paid for bill in bills)

        cash_inflows = sum(t.amount for t in transactions if t.amount > 0)
        cash_outflows = abs(sum(t.amount for t in transactions if t.amount < 0))

        # Calculate DSO and DPO
        dso = 0
        if total_invoiced > 0:
            avg_daily_sales = total_invoiced / days
            if avg_daily_sales > 0:
                dso = ar_aging['total'] / avg_daily_sales

        dpo = 0
        if total_billed > 0:
            avg_daily_purchases = total_billed / days
            if avg_daily_purchases > 0:
                dpo = ap_aging['total'] / avg_daily_purchases

        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'connected_sources': [s.integration_type.value for s in self.get_all_statuses() if s.is_connected],
            'accounts_receivable': {
                'total_invoiced': round(total_invoiced, 2),
                'total_collected': round(total_collected, 2),
                'collection_rate': round((total_collected / total_invoiced * 100) if total_invoiced > 0 else 0, 1),
                'outstanding': round(ar_aging['total'], 2),
                'aging': {
                    'current': round(ar_aging['current'], 2),
                    '1_30_days': round(ar_aging['1_30_days'], 2),
                    '31_60_days': round(ar_aging['31_60_days'], 2),
                    '61_90_days': round(ar_aging['61_90_days'], 2),
                    'over_90_days': round(ar_aging['over_90_days'], 2)
                },
                'invoice_count': len([i for i in invoices if i.amount_due > 0])
            },
            'accounts_payable': {
                'total_billed': round(total_billed, 2),
                'total_paid': round(total_paid, 2),
                'payment_rate': round((total_paid / total_billed * 100) if total_billed > 0 else 0, 1),
                'outstanding': round(ap_aging['total'], 2),
                'aging': {
                    'current': round(ap_aging['current'], 2),
                    '1_30_days': round(ap_aging['1_30_days'], 2),
                    '31_60_days': round(ap_aging['31_60_days'], 2),
                    '61_90_days': round(ap_aging['61_90_days'], 2),
                    'over_90_days': round(ap_aging['over_90_days'], 2)
                },
                'bill_count': len([b for b in bills if b.amount_due > 0])
            },
            'cash_flow': {
                'inflows': round(cash_inflows, 2),
                'outflows': round(cash_outflows, 2),
                'net_cash_flow': round(cash_inflows - cash_outflows, 2),
                'transaction_count': len(transactions)
            },
            'key_metrics': {
                'days_sales_outstanding': round(dso, 1),
                'days_payable_outstanding': round(dpo, 1),
                'cash_conversion_cycle': round(dso - dpo, 1),
                'working_capital': round(ar_aging['total'] - ap_aging['total'], 2)
            },
            'alerts': self._generate_alerts(ar_aging, ap_aging, dso, dpo, invoices, bills)
        }

    def _generate_alerts(self, ar_aging: Dict, ap_aging: Dict, dso: float, dpo: float,
                         invoices: List[UnifiedInvoice], bills: List[UnifiedBill]) -> List[Dict[str, Any]]:
        """Generate cash flow alerts based on analysis"""
        alerts = []

        # High overdue AR
        overdue_ar = ar_aging['over_90_days']
        if overdue_ar > 0:
            alerts.append({
                'type': 'warning',
                'category': 'Accounts Receivable',
                'message': f'${overdue_ar:,.2f} in receivables are over 90 days overdue',
                'recommendation': 'Consider implementing stricter collection procedures'
            })

        # High DSO
        if dso > 45:
            alerts.append({
                'type': 'warning',
                'category': 'Collections',
                'message': f'Days Sales Outstanding is {dso:.0f} days (industry average: 30-45)',
                'recommendation': 'Review credit terms and collection processes'
            })

        # Low DPO (paying too fast)
        if dpo < 15 and ap_aging['total'] > 0:
            alerts.append({
                'type': 'info',
                'category': 'Payments',
                'message': f'Days Payable Outstanding is {dpo:.0f} days',
                'recommendation': 'Consider negotiating longer payment terms to improve cash flow'
            })

        # Large upcoming payments
        upcoming_bills = [b for b in bills if b.due_date and b.amount_due > 0
                        and (b.due_date - datetime.utcnow()).days <= 7]
        if upcoming_bills:
            total_due = sum(b.amount_due for b in upcoming_bills)
            alerts.append({
                'type': 'info',
                'category': 'Upcoming Payments',
                'message': f'{len(upcoming_bills)} bills totaling ${total_due:,.2f} due within 7 days',
                'recommendation': 'Ensure sufficient cash reserves for upcoming obligations'
            })

        return alerts

    # ========== Token Storage ==========

    def _get_token_path(self, integration_type: IntegrationType) -> str:
        """Get the file path for storing tokens"""
        return os.path.join(self.storage_path, f'{integration_type.value}_token.json')

    def _store_token(self, integration_type: IntegrationType, token_data: Dict[str, Any]):
        """Store OAuth token to file"""
        token_path = self._get_token_path(integration_type)
        with open(token_path, 'w') as f:
            json.dump(token_data, f)

    def _load_stored_token(self, integration_type: IntegrationType):
        """Load stored OAuth token from file"""
        token_path = self._get_token_path(integration_type)

        if not os.path.exists(token_path):
            return

        try:
            with open(token_path, 'r') as f:
                token_data = json.load(f)

            if integration_type == IntegrationType.QUICKBOOKS and self._quickbooks_client:
                self._quickbooks_client.set_token(QuickBooksToken.from_dict(token_data))
            elif integration_type == IntegrationType.XERO and self._xero_client:
                self._xero_client.set_token(XeroToken.from_dict(token_data))

        except Exception as e:
            logger.error(f"Failed to load stored token for {integration_type}: {e}")


# Factory function for easy creation
def create_integration_manager(demo_mode: bool = False) -> IntegrationManager:
    """Create an IntegrationManager with appropriate configuration"""
    manager = IntegrationManager()

    if demo_mode:
        manager.enable_demo_mode()
    else:
        # Configure from environment variables if available
        if os.getenv('QUICKBOOKS_CLIENT_ID'):
            manager.configure_quickbooks()
        if os.getenv('XERO_CLIENT_ID'):
            manager.configure_xero()

    return manager
