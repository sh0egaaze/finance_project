"""
Роутеры API
"""
from .auth import router as auth_router
from .transactions import router as transactions_router
from .categories import router as categories_router
from .dashboard import router as dashboard_router
from .reminders import router as reminders_router
from .currency import router as currency_router
from .tbank import router as tbank_router

__all__ = [
    "auth_router",
    "transactions_router",
    "categories_router",
    "dashboard_router",
    "reminders_router",
    "currency_router",
    "tbank_router",
]
