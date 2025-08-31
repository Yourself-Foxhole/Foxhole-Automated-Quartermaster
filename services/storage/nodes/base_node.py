"""
PersistentBaseNode - Foundation class inheriting from ZODB Persistent.

Provides the base functionality for all persistent node types with
common attributes, methods, and ZODB integration patterns.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from persistent import Persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping

logger = logging.getLogger(__name__)


class PersistentBaseNode(Persistent):
    """
    Foundation class for all persistent node types.

    Inherits from ZODB Persistent to provide automatic persistence,
    transaction safety, and change tracking for node objects.
    """

    def __init__(
        self,
        node_id: Optional[str] = None,
        name: str = "",
        node_type: str = "base",
        **kwargs,
    ):
        """
        Initialize base persistent node.

        Args:
            node_id: Unique identifier for the node (auto-generated if None)
            name: Human-readable name for the node
            node_type: Type classification for the node
            **kwargs: Additional attributes to set on the node
        """
        super().__init__()

        # Core identification
        self.node_id = node_id or str(uuid.uuid4())
        self.name = name
        self.node_type = node_type

        # Timestamps
        self.created_at = datetime.utcnow()
        self.modified_at = datetime.utcnow()

        # Persistent collections for node data
        self.attributes = PersistentMapping()
        self.metadata = PersistentMapping()
        self.tags = PersistentList()

        # Graph connectivity information
        self.incoming_edges = PersistentList()
        self.outgoing_edges = PersistentList()

        # Status and state tracking
        self.is_active = True
        self.status = "initialized"

        # Set additional attributes from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.attributes[key] = value

        logger.debug(f"Created {node_type} node: {self.node_id} ({name})")

    def __repr__(self):
        """String representation of the node."""
        return f"{self.__class__.__name__}(id={self.node_id!r}, name={self.name!r}, type={self.node_type!r})"

    def __str__(self):
        """Human-readable string representation."""
        return f"{self.name} ({self.node_type})"

    def update_modified_time(self):
        """Update the modification timestamp and mark object as changed."""
        self.modified_at = datetime.utcnow()
        self._p_changed = True

    def set_attribute(self, key: str, value: Any):
        """
        Set an attribute on the node.

        Args:
            key: Attribute name
            value: Attribute value
        """
        self.attributes[key] = value
        self.update_modified_time()

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """
        Get an attribute from the node.

        Args:
            key: Attribute name
            default: Default value if attribute not found

        Returns:
            Attribute value or default
        """
        return self.attributes.get(key, default)

    def remove_attribute(self, key: str) -> bool:
        """
        Remove an attribute from the node.

        Args:
            key: Attribute name

        Returns:
            True if attribute was removed, False if not found
        """
        if key in self.attributes:
            del self.attributes[key]
            self.update_modified_time()
            return True
        return False

    def add_tag(self, tag: str):
        """
        Add a tag to the node.

        Args:
            tag: Tag to add
        """
        if tag not in self.tags:
            self.tags.append(tag)
            self.update_modified_time()

    def remove_tag(self, tag: str) -> bool:
        """
        Remove a tag from the node.

        Args:
            tag: Tag to remove

        Returns:
            True if tag was removed, False if not found
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self.update_modified_time()
            return True
        return False

    def has_tag(self, tag: str) -> bool:
        """
        Check if node has a specific tag.

        Args:
            tag: Tag to check

        Returns:
            True if node has the tag
        """
        return tag in self.tags

    def set_metadata(self, key: str, value: Any):
        """
        Set metadata on the node.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        self.update_modified_time()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata from the node.

        Args:
            key: Metadata key
            default: Default value if metadata not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def add_incoming_edge(self, edge_info: Dict[str, Any]):
        """
        Register an incoming edge to this node.

        Args:
            edge_info: Dictionary containing edge information
        """
        edge_data = PersistentMapping(edge_info)
        self.incoming_edges.append(edge_data)
        self.update_modified_time()

    def add_outgoing_edge(self, edge_info: Dict[str, Any]):
        """
        Register an outgoing edge from this node.

        Args:
            edge_info: Dictionary containing edge information
        """
        edge_data = PersistentMapping(edge_info)
        self.outgoing_edges.append(edge_data)
        self.update_modified_time()

    def remove_incoming_edge(self, edge_id: str) -> bool:
        """
        Remove an incoming edge by ID.

        Args:
            edge_id: ID of the edge to remove

        Returns:
            True if edge was removed, False if not found
        """
        for i, edge in enumerate(self.incoming_edges):
            if edge.get("edge_id") == edge_id:
                del self.incoming_edges[i]
                self.update_modified_time()
                return True
        return False

    def remove_outgoing_edge(self, edge_id: str) -> bool:
        """
        Remove an outgoing edge by ID.

        Args:
            edge_id: ID of the edge to remove

        Returns:
            True if edge was removed, False if not found
        """
        for i, edge in enumerate(self.outgoing_edges):
            if edge.get("edge_id") == edge_id:
                del self.outgoing_edges[i]
                self.update_modified_time()
                return True
        return False

    def get_incoming_edges(self) -> List[Dict[str, Any]]:
        """Get list of incoming edge information."""
        return [dict(edge) for edge in self.incoming_edges]

    def get_outgoing_edges(self) -> List[Dict[str, Any]]:
        """Get list of outgoing edge information."""
        return [dict(edge) for edge in self.outgoing_edges]

    def activate(self):
        """Activate the node."""
        self.is_active = True
        self.status = "active"
        self.update_modified_time()

    def deactivate(self):
        """Deactivate the node."""
        self.is_active = False
        self.status = "inactive"
        self.update_modified_time()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert node to dictionary representation.

        Returns:
            Dictionary representation of the node
        """
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "is_active": self.is_active,
            "status": self.status,
            "attributes": dict(self.attributes),
            "metadata": dict(self.metadata),
            "tags": list(self.tags),
            "incoming_edges_count": len(self.incoming_edges),
            "outgoing_edges_count": len(self.outgoing_edges),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersistentBaseNode":
        """
        Create node from dictionary representation.

        Args:
            data: Dictionary containing node data

        Returns:
            New node instance
        """
        # Extract core fields
        node_id = data.get("node_id")
        name = data.get("name", "")
        node_type = data.get("node_type", "base")

        # Create node
        node = cls(node_id=node_id, name=name, node_type=node_type)

        # Set additional fields
        if "is_active" in data:
            node.is_active = data["is_active"]
        if "status" in data:
            node.status = data["status"]

        # Set attributes
        if "attributes" in data:
            node.attributes.update(data["attributes"])

        # Set metadata
        if "metadata" in data:
            node.metadata.update(data["metadata"])

        # Set tags
        if "tags" in data:
            node.tags.extend(data["tags"])

        return node

    def validate(self) -> Dict[str, Any]:
        """
        Validate the node's data integrity.

        Returns:
            Dictionary with validation results
        """
        issues = []

        # Check required fields
        if not self.node_id:
            issues.append("Node ID is required")
        if not self.name:
            issues.append("Node name is required")
        if not self.node_type:
            issues.append("Node type is required")

        # Check data consistency
        if self.created_at and self.modified_at and self.created_at > self.modified_at:
            issues.append("Created time is after modified time")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "node_id": self.node_id,
            "node_type": self.node_type,
        }
