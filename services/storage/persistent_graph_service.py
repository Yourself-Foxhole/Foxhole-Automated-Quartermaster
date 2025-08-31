"""
PersistentGraphService - High-level API for graph operations with performance caching.

Provides a service layer for managing persistent graphs with caching,
batch operations, and optimized performance for complex graph operations.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
import logging
import time
from contextlib import contextmanager
from .zodb_manager import zodb_manager
from .graph_storage import GraphStorage
from .persistent_networkx_graph import PersistentNetworkXGraph
from .nodes import PersistentBaseNode, PersistentInventoryNode, PersistentProductionNode, PersistentTaskNode

logger = logging.getLogger(__name__)


class PersistentGraphService:
    """
    High-level API for graph operations with performance caching.
    
    Provides a service layer that combines ZODB storage with performance
    optimizations including caching, batch operations, and efficient queries.
    """
    
    def __init__(self, cache_size: int = 1000, cache_ttl: int = 3600):
        """
        Initialize the graph service.
        
        Args:
            cache_size: Maximum number of cached items
            cache_ttl: Cache time-to-live in seconds
        """
        self.zodb_manager = zodb_manager
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_size = cache_size
        self._cache_ttl = cache_ttl
        
        # Performance metrics
        self._operation_counts = {
            'reads': 0,
            'writes': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        logger.info("PersistentGraphService initialized")
    
    def _get_storage(self) -> GraphStorage:
        """Get or create the graph storage container."""
        with self.zodb_manager.read_only_transaction() as root:
            if 'graph_storage' not in root:
                with self.zodb_manager.transaction() as root:
                    root['graph_storage'] = GraphStorage()
                logger.info("Created new GraphStorage container")
            
            return root['graph_storage']
    
    def _cache_key(self, operation: str, *args) -> str:
        """Generate cache key for operation."""
        return f"{operation}:{':'.join(str(arg) for arg in args)}"
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache_timestamps:
            return False
        
        age = time.time() - self._cache_timestamps[key]
        return age < self._cache_ttl
    
    def _cache_get(self, key: str) -> Optional[Any]:
        """Get item from cache if valid."""
        if key in self._cache and self._is_cache_valid(key):
            self._operation_counts['cache_hits'] += 1
            return self._cache[key]
        
        self._operation_counts['cache_misses'] += 1
        return None
    
    def _cache_set(self, key: str, value: Any):
        """Set item in cache."""
        # Implement simple LRU eviction
        if len(self._cache) >= self._cache_size:
            # Remove oldest entry
            oldest_key = min(self._cache_timestamps.keys(), 
                           key=lambda k: self._cache_timestamps[k])
            del self._cache[oldest_key]
            del self._cache_timestamps[oldest_key]
        
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()
    
    def _invalidate_cache_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        keys_to_remove = [k for k in self._cache.keys() if pattern in k]
        for key in keys_to_remove:
            del self._cache[key]
            del self._cache_timestamps[key]
    
    # Graph Management
    
    def create_graph(self, graph_id: str, graph_type: str = "DiGraph", 
                    graph_name: str = "", metadata: Optional[Dict] = None) -> PersistentNetworkXGraph:
        """
        Create a new persistent graph.
        
        Args:
            graph_id: Unique identifier for the graph
            graph_type: Type of NetworkX graph
            graph_name: Human-readable name
            metadata: Optional metadata
            
        Returns:
            New persistent graph instance
        """
        # Check if graph already exists
        if self.graph_exists(graph_id):
            raise ValueError(f"Graph {graph_id} already exists")
        
        # Create the graph
        graph = PersistentNetworkXGraph(
            graph_type=graph_type,
            graph_id=graph_id,
            graph_name=graph_name or graph_id
        )
        
        # Store in ZODB
        with self.zodb_manager.transaction() as root:
            storage = root.get('graph_storage')
            if storage is None:
                storage = GraphStorage()
                root['graph_storage'] = storage
            
            # Determine graph category based on type/metadata
            category = self._determine_graph_category(metadata)
            storage.register_graph(graph_id, category, graph, metadata)
        
        # Invalidate relevant cache entries
        self._invalidate_cache_pattern('list_graphs')
        self._invalidate_cache_pattern(f'graph:{graph_id}')
        
        self._operation_counts['writes'] += 1
        logger.info(f"Created graph {graph_id} ({graph_type})")
        
        return graph
    
    def get_graph(self, graph_id: str) -> Optional[PersistentNetworkXGraph]:
        """
        Get a graph by ID.
        
        Args:
            graph_id: Graph identifier
            
        Returns:
            Graph instance or None if not found
        """
        cache_key = self._cache_key('graph', graph_id)
        cached_graph = self._cache_get(cache_key)
        
        if cached_graph is not None:
            return cached_graph
        
        with self.zodb_manager.read_only_transaction() as root:
            storage = root.get('graph_storage')
            if storage is None:
                return None
            
            graph = storage.get_graph(graph_id)
            
            if graph is not None:
                self._cache_set(cache_key, graph)
                self._operation_counts['reads'] += 1
            
            return graph
    
    def delete_graph(self, graph_id: str) -> bool:
        """
        Delete a graph.
        
        Args:
            graph_id: Graph identifier
            
        Returns:
            True if graph was deleted
        """
        with self.zodb_manager.transaction() as root:
            storage = root.get('graph_storage')
            if storage is None:
                return False
            
            success = storage.remove_graph(graph_id)
            
            if success:
                # Invalidate cache
                self._invalidate_cache_pattern(f'graph:{graph_id}')
                self._invalidate_cache_pattern('list_graphs')
                
                self._operation_counts['writes'] += 1
                logger.info(f"Deleted graph {graph_id}")
            
            return success
    
    def graph_exists(self, graph_id: str) -> bool:
        """
        Check if a graph exists.
        
        Args:
            graph_id: Graph identifier
            
        Returns:
            True if graph exists
        """
        cache_key = self._cache_key('exists', graph_id)
        cached_result = self._cache_get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        with self.zodb_manager.read_only_transaction() as root:
            storage = root.get('graph_storage')
            if storage is None:
                return False
            
            exists = graph_id in storage.graph_registry
            self._cache_set(cache_key, exists)
            
            return exists
    
    def list_graphs(self, graph_type: Optional[str] = None) -> List[str]:
        """
        List all graph IDs.
        
        Args:
            graph_type: Optional filter by graph type
            
        Returns:
            List of graph IDs
        """
        cache_key = self._cache_key('list_graphs', graph_type or 'all')
        cached_list = self._cache_get(cache_key)
        
        if cached_list is not None:
            return cached_list
        
        with self.zodb_manager.read_only_transaction() as root:
            storage = root.get('graph_storage')
            if storage is None:
                return []
            
            graph_list = storage.list_graphs(graph_type)
            self._cache_set(cache_key, graph_list)
            
            return graph_list
    
    def get_graph_info(self, graph_id: str) -> Optional[Dict]:
        """
        Get graph metadata information.
        
        Args:
            graph_id: Graph identifier
            
        Returns:
            Graph information dictionary
        """
        cache_key = self._cache_key('graph_info', graph_id)
        cached_info = self._cache_get(cache_key)
        
        if cached_info is not None:
            return cached_info
        
        with self.zodb_manager.read_only_transaction() as root:
            storage = root.get('graph_storage')
            if storage is None:
                return None
            
            info = storage.get_graph_info(graph_id)
            
            if info is not None:
                self._cache_set(cache_key, info)
            
            return info
    
    # Node Management
    
    def create_node(self, graph_id: str, node_type: str, **kwargs) -> Optional[PersistentBaseNode]:
        """
        Create a persistent node and add it to a graph.
        
        Args:
            graph_id: Graph to add node to
            node_type: Type of node (base, inventory, production, task)
            **kwargs: Node attributes
            
        Returns:
            Created node instance
        """
        graph = self.get_graph(graph_id)
        if graph is None:
            logger.error(f"Graph {graph_id} not found")
            return None
        
        # Create appropriate node type
        node_classes = {
            'base': PersistentBaseNode,
            'inventory': PersistentInventoryNode,
            'production': PersistentProductionNode,
            'task': PersistentTaskNode
        }
        
        if node_type not in node_classes:
            logger.error(f"Unknown node type: {node_type}")
            return None
        
        node_class = node_classes[node_type]
        node = node_class(**kwargs)
        
        # Add to graph
        graph.add_node(node.node_id, persistent_node=node, **kwargs)
        
        # Invalidate relevant cache
        self._invalidate_cache_pattern(f'graph:{graph_id}')
        
        self._operation_counts['writes'] += 1
        logger.debug(f"Created {node_type} node {node.node_id} in graph {graph_id}")
        
        return node
    
    def get_node(self, graph_id: str, node_id: str) -> Optional[PersistentBaseNode]:
        """
        Get a node from a graph.
        
        Args:
            graph_id: Graph identifier
            node_id: Node identifier
            
        Returns:
            Node instance or None
        """
        graph = self.get_graph(graph_id)
        if graph is None:
            return None
        
        if node_id not in graph.nodes:
            return None
        
        node_data = graph.nodes[node_id]
        return node_data.get('persistent_node')
    
    def update_node(self, graph_id: str, node_id: str, **updates) -> bool:
        """
        Update a node's attributes.
        
        Args:
            graph_id: Graph identifier
            node_id: Node identifier
            **updates: Attributes to update
            
        Returns:
            True if node was updated
        """
        node = self.get_node(graph_id, node_id)
        if node is None:
            return False
        
        # Update node attributes
        for key, value in updates.items():
            if hasattr(node, key):
                setattr(node, key, value)
            else:
                node.set_attribute(key, value)
        
        node.update_modified_time()
        
        # Invalidate cache
        self._invalidate_cache_pattern(f'graph:{graph_id}')
        
        self._operation_counts['writes'] += 1
        return True
    
    def remove_node(self, graph_id: str, node_id: str) -> bool:
        """
        Remove a node from a graph.
        
        Args:
            graph_id: Graph identifier
            node_id: Node identifier
            
        Returns:
            True if node was removed
        """
        graph = self.get_graph(graph_id)
        if graph is None:
            return False
        
        if node_id not in graph.nodes:
            return False
        
        graph.remove_node(node_id)
        
        # Invalidate cache
        self._invalidate_cache_pattern(f'graph:{graph_id}')
        
        self._operation_counts['writes'] += 1
        logger.debug(f"Removed node {node_id} from graph {graph_id}")
        
        return True
    
    # Batch Operations
    
    @contextmanager
    def batch_operation(self, graph_id: str):
        """
        Context manager for batch operations on a graph.
        
        Args:
            graph_id: Graph identifier
            
        Yields:
            Graph instance in batch mode
        """
        graph = self.get_graph(graph_id)
        if graph is None:
            raise ValueError(f"Graph {graph_id} not found")
        
        graph.start_batch_mode()
        try:
            yield graph
        finally:
            graph.end_batch_mode()
            # Invalidate cache after batch operation
            self._invalidate_cache_pattern(f'graph:{graph_id}')
            self._operation_counts['writes'] += 1
    
    # Utility Methods
    
    def _determine_graph_category(self, metadata: Optional[Dict]) -> str:
        """Determine graph category from metadata."""
        if not metadata:
            return 'production'  # Default category
        
        # Logic to determine category based on metadata
        category_hints = {
            'production': ['recipe', 'factory', 'manufacturing'],
            'task': ['workflow', 'job', 'process'],
            'inventory': ['storage', 'warehouse', 'supply'],
            'transport': ['route', 'logistics', 'shipping']
        }
        
        metadata_str = str(metadata).lower()
        for category, hints in category_hints.items():
            if any(hint in metadata_str for hint in hints):
                return category
        
        return 'production'  # Default
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get service performance statistics."""
        total_operations = sum(self._operation_counts.values())
        cache_hit_rate = (self._operation_counts['cache_hits'] / 
                         max(1, self._operation_counts['cache_hits'] + self._operation_counts['cache_misses'])) * 100
        
        return {
            'operation_counts': dict(self._operation_counts),
            'total_operations': total_operations,
            'cache_hit_rate_percent': cache_hit_rate,
            'cache_size': len(self._cache),
            'cache_capacity': self._cache_size,
            'cache_ttl_seconds': self._cache_ttl
        }
    
    def clear_cache(self):
        """Clear the performance cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("Service cache cleared")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the service."""
        health = {
            'status': 'healthy',
            'issues': [],
            'timestamp': time.time()
        }
        
        try:
            # Test ZODB connection
            zodb_health = self.zodb_manager.health_check()
            if zodb_health['status'] != 'healthy':
                health['status'] = 'unhealthy'
                health['issues'].extend(zodb_health['issues'])
            
            # Test graph storage access
            with self.zodb_manager.read_only_transaction() as root:
                storage = root.get('graph_storage')
                if storage is None:
                    health['issues'].append("Graph storage not initialized")
                    health['status'] = 'warning'
                else:
                    # Validate storage integrity
                    validation = storage.validate_integrity()
                    if not validation['is_valid']:
                        health['status'] = 'warning'
                        health['issues'].extend(validation['issues'])
            
            # Check cache health
            if len(self._cache) >= self._cache_size * 0.9:
                health['issues'].append("Cache is nearly full")
                health['status'] = 'warning'
            
        except Exception as e:
            health['status'] = 'unhealthy'
            health['issues'].append(f"Health check failed: {e}")
        
        return health


# Global service instance
graph_service = PersistentGraphService()