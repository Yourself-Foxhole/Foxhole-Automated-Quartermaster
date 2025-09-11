"""ZODB connection wrapper for persistent storage.

This module provides a ZODBConnection class for managing a ZODB database,
with simple get/set methods for Discord config and other persistent data.
"""

import shutil
from pathlib import Path

import transaction  # type: ignore[import]
from persistent.mapping import (  # type: ignore[attr-defined,import]
    PersistentMapping,
)
from ZODB import DB  # type: ignore[import] # NOSONAR(S7632)
from ZODB.FileStorage import FileStorage  # type: ignore[import]


class ZODBConnection:
    """Wrapper for ZODB database connection and config storage."""

    def __init__(self, db_path: str = "zodb.fs") -> None:
        """Initialize the ZODBConnection with the path to the database file."""
        self.db_path = db_path
        self._db = None
        self._conn = None
        self._root = None

    def open(self) -> None:
        """Open the ZODB database and initialize root mapping if needed."""
        storage = FileStorage(self.db_path)
        db = DB(storage)
        self._db = db
        if self._db is None:
            msg = "Failed to initialize ZODB DB object."
            raise RuntimeError(msg)
        self._conn = self._db.open()
        self._root = self._conn.root()
        if "config" not in self._root:
            self._root["config"] = PersistentMapping()
            transaction.commit()

    def close(self) -> None:
        """Close the ZODB connection and database."""
        if self._conn:
            self._conn.close()
        if self._db:
            self._db.close()

    @property
    def config(self) -> PersistentMapping:
        """Return the persistent config mapping."""
        if self._root is None:
            self.open()
        if self._root is None:
            msg = "ZODB root is not initialized after opening the database."
            raise RuntimeError(msg)
        return self._root["config"]

    def get_config(self, key: str, default: object = None) -> object:
        """Get a config value by key."""
        return self.config.get(key, default)

    def set_config(self, key: str, value: object) -> None:
        """Set a config value and commit the transaction."""
        self.config[key] = value
        transaction.commit()


# ZODBFileManager: Utility for managing ZODB file lifecycle (creation, backup, deletion)  # noqa: E501, RUF100 # pylint: disable=line-too-long
class ZODBFileManager:
    """Manager for ZODB database file operations (create, backup, delete)."""

    def __init__(self, db_path: str = "zodb.fs") -> None:
        """Initialize the file manager with the path to the ZODB file."""
        self.db_path = Path(db_path)

    def exists(self) -> bool:
        """Check if the ZODB file exists."""
        return self.db_path.exists()

    def backup(self, backup_path: str | None = None) -> Path:
        """Backup the ZODB file to a specified path."""
        if not self.exists():
            msg = f"{self.db_path} does not exist."
            raise FileNotFoundError(msg)
        backup = (Path(backup_path) if backup_path else
                  self.db_path.with_suffix(self.db_path.suffix + ".bak"))
        shutil.copy2(self.db_path, backup)
        return backup

    def delete(self) -> None:
        """Delete the ZODB file."""
        if self.exists():
            # Disabled for safety: do not allow programmatic deletion of the database file.  # noqa: E501, RUF100 # pylint: disable=line-too-long
            # If you need to remove the database, please delete it manually.
            msg = (
                "Database deletion is disabled for safety. "
                "Please remove the file manually if needed. "
                f" (File: {self.db_path})"
            )
            raise NotImplementedError(msg)
