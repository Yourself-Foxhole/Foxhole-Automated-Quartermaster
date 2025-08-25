"""
Foxhole Automated Quartermaster - Multi-tenant Discord bot for logistics tracking.

This package provides a multi-tenant Discord bot system that allows multiple
regiments to use the bot for tracking Foxhole game logistics without data
leakage between tenants.
"""

__version__ = "0.1.0"
__author__ = "Yourself-Foxhole"
__description__ = "Discord Bot to track Logistics in the game of Foxhole, tracking what to move where, and when."

from .core.bot import TenantBot
from .core.tenant import TenantManager, Tenant
from .models import User, UserRole, Permission, TenantContext

__all__ = [
    'TenantBot',
    'TenantManager', 
    'Tenant',
    'User',
    'UserRole',
    'Permission',
    'TenantContext'
]