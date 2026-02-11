"""
External Data Integrations for Cash Flow Intelligence

Provides connections to:
- QuickBooks Online
- Xero Accounting
- Bank feeds (Plaid)
"""

from .quickbooks_client import QuickBooksClient, QuickBooksConfig
from .xero_client import XeroClient, XeroConfig
from .integration_manager import IntegrationManager, IntegrationType

__all__ = [
    'QuickBooksClient',
    'QuickBooksConfig',
    'XeroClient',
    'XeroConfig',
    'IntegrationManager',
    'IntegrationType'
]
