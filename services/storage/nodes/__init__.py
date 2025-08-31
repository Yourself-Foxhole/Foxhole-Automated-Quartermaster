"""
Persistent Node Classes for ZODB-based graph storage.

This module provides persistent node implementations that inherit from
ZODB Persistent, enabling direct storage of complex node objects with
full data integrity and transactional safety.
"""

from .base_node import PersistentBaseNode
from .inventory_node import PersistentInventoryNode
from .production_node import PersistentProductionNode
from .task_node import PersistentTaskNode

__all__ = [
    'PersistentBaseNode',
    'PersistentInventoryNode',
    'PersistentProductionNode',
    'PersistentTaskNode'
]