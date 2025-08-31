"""
Graph Storage Container - Organized persistent storage of different graph types.

Provides a structured container for storing multiple graph types with
metadata and organized access patterns.
"""

from typing import Dict, List, Optional, Any
import logging
from persistent import Persistent
from persistent.mapping import PersistentMapping
from persistent.list import PersistentList
import BTrees.OOBTree

logger = logging.getLogger(__name__)


class GraphStorage(Persistent):
    """
    Container for organized persistent storage of different graph types.
    
    Provides structured storage for production graphs, task graphs, inventory
    networks, and other graph-based data with metadata and versioning.
    """
    
    def __init__(self):
        """Initialize the graph storage container."""
        super().__init__()
        
        # Main storage containers for different graph types
        self.production_graphs = BTrees.OOBTree.BTree()
        self.task_graphs = BTrees.OOBTree.BTree()
        self.inventory_networks = BTrees.OOBTree.BTree()
        self.transport_networks = BTrees.OOBTree.BTree()
        
        # Metadata storage
        self.metadata = PersistentMapping()
        self.graph_registry = PersistentMapping()
        
        # Version tracking
        self.version = "1.0.0"
        self.schema_version = 1
        
        # Initialize metadata
        self._initialize_metadata()
        
        logger.info("GraphStorage container initialized")
    
    def _initialize_metadata(self):
        """Initialize metadata structure."""
        self.metadata.update({
            'created_at': None,  # Will be set on first use
            'last_modified': None,
            'total_graphs': 0,
            'graph_types': PersistentList(['production', 'task', 'inventory', 'transport']),
            'statistics': PersistentMapping()
        })
    
    def register_graph(self, graph_id: str, graph_type: str, graph_obj: Any, metadata: Optional[Dict] = None):
        """
        Register a graph in the appropriate storage container.
        
        Args:
            graph_id: Unique identifier for the graph
            graph_type: Type of graph ('production', 'task', 'inventory', 'transport')
            graph_obj: The graph object to store
            metadata: Optional metadata dictionary
        """
        if graph_type not in self.metadata['graph_types']:
            raise ValueError(f"Unknown graph type: {graph_type}. Supported types: {list(self.metadata['graph_types'])}")
        
        # Get the appropriate storage container
        storage_container = getattr(self, f"{graph_type}_graphs")
        
        # Store the graph
        storage_container[graph_id] = graph_obj
        
        # Update registry
        graph_info = PersistentMapping({
            'graph_id': graph_id,
            'graph_type': graph_type,
            'metadata': PersistentMapping(metadata or {}),
            'created_at': None,  # Should be set to current timestamp
            'last_modified': None
        })
        
        self.graph_registry[graph_id] = graph_info
        
        # Update statistics
        self._update_statistics()
        
        logger.info(f"Registered {graph_type} graph with ID: {graph_id}")
    
    def get_graph(self, graph_id: str) -> Optional[Any]:
        """
        Retrieve a graph by its ID.
        
        Args:
            graph_id: Unique identifier for the graph
            
        Returns:
            The graph object if found, None otherwise
        """
        if graph_id not in self.graph_registry:
            return None
        
        graph_info = self.graph_registry[graph_id]
        graph_type = graph_info['graph_type']
        storage_container = getattr(self, f"{graph_type}_graphs")
        
        return storage_container.get(graph_id)
    
    def remove_graph(self, graph_id: str) -> bool:
        """
        Remove a graph from storage.
        
        Args:
            graph_id: Unique identifier for the graph
            
        Returns:
            True if graph was removed, False if not found
        """
        if graph_id not in self.graph_registry:
            return False
        
        graph_info = self.graph_registry[graph_id]
        graph_type = graph_info['graph_type']
        storage_container = getattr(self, f"{graph_type}_graphs")
        
        # Remove from storage and registry
        del storage_container[graph_id]
        del self.graph_registry[graph_id]
        
        # Update statistics
        self._update_statistics()
        
        logger.info(f"Removed graph with ID: {graph_id}")
        return True
    
    def list_graphs(self, graph_type: Optional[str] = None) -> List[str]:
        """
        List all graph IDs, optionally filtered by type.
        
        Args:
            graph_type: Optional filter by graph type
            
        Returns:
            List of graph IDs
        """
        if graph_type is None:
            return list(self.graph_registry.keys())
        
        return [
            graph_id for graph_id, info in self.graph_registry.items()
            if info['graph_type'] == graph_type
        ]
    
    def get_graph_info(self, graph_id: str) -> Optional[Dict]:
        """
        Get metadata information about a graph.
        
        Args:
            graph_id: Unique identifier for the graph
            
        Returns:
            Dictionary with graph information or None if not found
        """
        if graph_id not in self.graph_registry:
            return None
        
        return dict(self.graph_registry[graph_id])
    
    def update_graph_metadata(self, graph_id: str, metadata: Dict):
        """
        Update metadata for a graph.
        
        Args:
            graph_id: Unique identifier for the graph
            metadata: Dictionary of metadata to update
        """
        if graph_id not in self.graph_registry:
            raise ValueError(f"Graph {graph_id} not found")
        
        graph_info = self.graph_registry[graph_id]
        graph_info['metadata'].update(metadata)
        graph_info['last_modified'] = None  # Should be set to current timestamp
        
        logger.info(f"Updated metadata for graph: {graph_id}")
    
    def _update_statistics(self):
        """Update storage statistics."""
        stats = PersistentMapping()
        
        for graph_type in self.metadata['graph_types']:
            storage_container = getattr(self, f"{graph_type}_graphs")
            stats[f"{graph_type}_count"] = len(storage_container)
        
        stats['total_graphs'] = sum(stats.values())
        
        self.metadata['statistics'] = stats
        self.metadata['last_modified'] = None  # Should be set to current timestamp
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        self._update_statistics()
        return dict(self.metadata['statistics'])
    
    def compact_storage(self):
        """Compact storage containers to optimize space."""
        for graph_type in self.metadata['graph_types']:
            storage_container = getattr(self, f"{graph_type}_graphs")
            # BTrees are self-optimizing, but we can trigger cleanup
            if hasattr(storage_container, '_p_activate'):
                storage_container._p_activate()
        
        logger.info("Storage compaction completed")
    
    def export_graph_list(self) -> List[Dict]:
        """Export a list of all graphs with their metadata."""
        graphs = []
        
        for graph_id, info in self.graph_registry.items():
            graph_data = dict(info)
            graph_data['metadata'] = dict(graph_data['metadata'])
            graphs.append(graph_data)
        
        return graphs
    
    def validate_integrity(self) -> Dict[str, Any]:
        """Validate the integrity of the storage container."""
        issues = []
        
        # Check that all registered graphs exist in storage
        for graph_id, info in self.graph_registry.items():
            graph_type = info['graph_type']
            storage_container = getattr(self, f"{graph_type}_graphs")
            
            if graph_id not in storage_container:
                issues.append(f"Graph {graph_id} registered but not found in {graph_type} storage")
        
        # Check for orphaned graphs in storage
        for graph_type in self.metadata['graph_types']:
            storage_container = getattr(self, f"{graph_type}_graphs")
            for graph_id in storage_container.keys():
                if graph_id not in self.graph_registry:
                    issues.append(f"Graph {graph_id} found in {graph_type} storage but not registered")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'total_registered': len(self.graph_registry),
            'total_stored': sum(
                len(getattr(self, f"{graph_type}_graphs"))
                for graph_type in self.metadata['graph_types']
            )
        }