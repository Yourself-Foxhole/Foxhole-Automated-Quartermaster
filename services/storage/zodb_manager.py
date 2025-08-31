"""
ZODB Manager - Singleton pattern for database connection management.

Provides centralized database connection management with transaction support,
automatic rollback on errors, and database maintenance utilities.
"""

import logging
import os
import threading
from contextlib import contextmanager
from typing import Any, Dict, Optional

import BTrees.OOBTree
import transaction
import ZODB
import ZODB.FileStorage
from persistent import Persistent

logger = logging.getLogger(__name__)


class ZODBManager:
    """
    Singleton ZODB manager for centralized database connection management.

    Provides thread-safe access to ZODB with transaction context managers,
    automatic rollback on errors, and database maintenance utilities.
    """

    _instance: Optional["ZODBManager"] = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = "data/storage/foxhole_graphs.db") -> "ZODBManager":
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = "data/storage/foxhole_graphs.db"):
        """Initialize ZODB manager with database path."""
        if self._initialized:
            return

        self.db_path = db_path
        self._ensure_directory()

        # Initialize ZODB storage and database
        self.storage = ZODB.FileStorage.FileStorage(self.db_path)
        self.db = ZODB.DB(self.storage)
        self._connection = None
        self._root = None

        # Thread local storage for connections
        self._local = threading.local()

        self._initialized = True
        logger.info(f"ZODB Manager initialized with database at {self.db_path}")

    def _ensure_directory(self):
        """Ensure the directory for the database file exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    @property
    def connection(self):
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = self.db.open()
        return self._local.connection

    @property
    def root(self):
        """Get the root object of the database."""
        if not hasattr(self._local, "root") or self._local.root is None:
            self._local.root = self.connection.root()
        return self._local.root

    @contextmanager
    def transaction(self):
        """
        Transaction context manager with automatic rollback on errors.

        Example:
            with zodb_manager.transaction():
                # Perform operations
                root['key'] = value
                # Automatically commits on success, rolls back on exception
        """
        try:
            yield self.root
            transaction.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            transaction.abort()
            logger.error(f"Transaction aborted due to error: {e}")
            raise

    @contextmanager
    def read_only_transaction(self):
        """
        Read-only transaction context manager for optimized read operations.

        Example:
            with zodb_manager.read_only_transaction() as root:
                data = root['key']
        """
        try:
            yield self.root
        except Exception as e:
            logger.error(f"Read-only transaction failed: {e}")
            raise

    def close(self):
        """Close database connections and storage."""
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
            self._local.root = None

        if hasattr(self, "db") and self.db:
            self.db.close()

        if hasattr(self, "storage") and self.storage:
            self.storage.close()

        logger.info("ZODB Manager closed")

    def pack(self, days: int = 7):
        """
        Pack the database to remove old revisions and reclaim space.

        Args:
            days: Keep revisions from the last N days
        """
        import time

        pack_time = time.time() - (days * 24 * 60 * 60)

        try:
            self.db.pack(pack_time)
            logger.info(
                f"Database packed successfully, removed revisions older than {days} days"
            )
        except Exception as e:
            logger.error(f"Database packing failed: {e}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics and health information."""
        stats = {}

        try:
            # Database size
            if os.path.exists(self.db_path):
                stats["db_size_bytes"] = os.path.getsize(self.db_path)
                stats["db_size_mb"] = round(stats["db_size_bytes"] / (1024 * 1024), 2)

            # Connection pool statistics
            stats["pool_size"] = self.db.getPoolSize()
            stats["cache_size"] = self.db.getCacheSize()

            # Root object information
            with self.read_only_transaction() as root:
                stats["root_keys"] = list(root.keys()) if hasattr(root, "keys") else []
                stats["num_root_objects"] = len(stats["root_keys"])

        except Exception as e:
            logger.error(f"Failed to collect database statistics: {e}")
            stats["error"] = str(e)

        return stats

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the database."""
        health = {"status": "healthy", "issues": [], "timestamp": "now"}

        try:
            # Test database connection
            with self.read_only_transaction() as root:
                # Try to access root
                _ = list(root.keys()) if hasattr(root, "keys") else []

            # Check file system
            if not os.path.exists(self.db_path):
                health["issues"].append("Database file does not exist")
                health["status"] = "unhealthy"

            # Check write permissions
            db_dir = os.path.dirname(self.db_path)
            if not os.access(db_dir, os.W_OK):
                health["issues"].append("No write permission to database directory")
                health["status"] = "warning"

        except Exception as e:
            health["status"] = "unhealthy"
            health["issues"].append(f"Database access failed: {e}")

        return health

    def backup(self, backup_path: str):
        """Create a backup of the database."""
        import shutil

        try:
            # Ensure backup directory exists
            backup_dir = os.path.dirname(backup_path)
            if backup_dir and not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)

            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            raise

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (mainly for testing)."""
        with cls._lock:
            if cls._instance:
                cls._instance.close()
            cls._instance = None


# Global instance for easy access
zodb_manager = ZODBManager()
