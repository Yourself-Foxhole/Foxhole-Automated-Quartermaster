"""
ZODB-based persistent storage system for NetworkX graphs.

This module provides a modern object-oriented database solution optimized
for complex graph structures, replacing the legacy Peewee/SQLite approach.
"""

from .zodb_manager import ZODBManager, zodb_manager
from .graph_storage import GraphStorage
from .persistent_graph_service import PersistentGraphService, graph_service
from .persistent_networkx_graph import PersistentNetworkXGraph
from .migration_manager import GraphMigrationManager, migration_manager

__all__ = [
    'ZODBManager',
    'zodb_manager',
    'GraphStorage',
    'PersistentGraphService',
    'graph_service',
    'PersistentNetworkXGraph',
    'GraphMigrationManager',
    'migration_manager'
]