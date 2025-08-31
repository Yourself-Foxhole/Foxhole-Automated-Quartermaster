"""
PersistentNetworkXGraph - ZODB-compatible wrapper maintaining full NetworkX API compatibility.

Provides a persistent NetworkX graph implementation that seamlessly integrates
with ZODB while maintaining full compatibility with NetworkX operations.
"""

import copy
import logging
import pickle
from typing import Any, Dict, Iterator, List, Optional, Union

import networkx as nx
from persistent import Persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping

logger = logging.getLogger(__name__)


class PersistentNetworkXGraph(Persistent):
    """
    ZODB-compatible wrapper for NetworkX graphs.

    Maintains full NetworkX API compatibility while providing automatic
    persistence, transaction safety, and efficient storage of graph structures.
    """

    def __init__(self, graph_type: str = "DiGraph", data=None, **kwargs):
        """
        Initialize persistent NetworkX graph.

        Args:
            graph_type: Type of NetworkX graph (Graph, DiGraph, MultiGraph, MultiDiGraph)
            data: Initial graph data
            **kwargs: Additional graph attributes
        """
        super().__init__()

        # Graph metadata
        self.graph_id = kwargs.pop("graph_id", None)
        self.graph_name = kwargs.pop("graph_name", "")
        self.graph_type = graph_type
        self.version = kwargs.pop("version", "1.0.0")

        # Create the underlying NetworkX graph
        graph_classes = {
            "Graph": nx.Graph,
            "DiGraph": nx.DiGraph,
            "MultiGraph": nx.MultiGraph,
            "MultiDiGraph": nx.MultiDiGraph,
        }

        if graph_type not in graph_classes:
            raise ValueError(f"Unsupported graph type: {graph_type}")

        self._graph_class = graph_classes[graph_type]
        self._graph = self._graph_class(data, **kwargs)

        # Persistent storage for graph data
        self._persistent_nodes = PersistentMapping()
        self._persistent_edges = PersistentMapping()
        self._persistent_graph_attrs = PersistentMapping()

        # Synchronize with the NetworkX graph
        self._sync_to_persistent()

        # Performance optimization flags
        self._auto_sync = True
        self._batch_mode = False
        self._pending_changes = []

        logger.debug(
            f"Created persistent {graph_type} with {len(self._graph.nodes)} nodes and {len(self._graph.edges)} edges"
        )

    def _sync_to_persistent(self):
        """Synchronize NetworkX graph data to persistent storage."""
        # Sync nodes
        self._persistent_nodes.clear()
        for node, attrs in self._graph.nodes(data=True):
            self._persistent_nodes[node] = PersistentMapping(attrs)

        # Sync edges
        self._persistent_edges.clear()
        if self._graph.is_multigraph():
            # Handle multigraph edges
            for u, v, key, attrs in self._graph.edges(keys=True, data=True):
                edge_key = (u, v, key)
                self._persistent_edges[edge_key] = PersistentMapping(attrs)
        else:
            # Handle regular edges
            for u, v, attrs in self._graph.edges(data=True):
                edge_key = (u, v)
                self._persistent_edges[edge_key] = PersistentMapping(attrs)

        # Sync graph attributes
        self._persistent_graph_attrs.clear()
        self._persistent_graph_attrs.update(self._graph.graph)

        self._p_changed = True

    def _sync_from_persistent(self):
        """Synchronize persistent storage to NetworkX graph."""
        # Recreate NetworkX graph
        self._graph = self._graph_class()

        # Add nodes
        for node, attrs in self._persistent_nodes.items():
            self._graph.add_node(node, **dict(attrs))

        # Add edges
        if self._graph.is_multigraph():
            # Handle multigraph edges
            for (u, v, key), attrs in self._persistent_edges.items():
                self._graph.add_edge(u, v, key=key, **dict(attrs))
        else:
            # Handle regular edges
            for (u, v), attrs in self._persistent_edges.items():
                self._graph.add_edge(u, v, **dict(attrs))

        # Set graph attributes
        self._graph.graph.update(dict(self._persistent_graph_attrs))

    def _mark_changed(self):
        """Mark the object as changed for ZODB."""
        if self._auto_sync:
            self._sync_to_persistent()
        self._p_changed = True

    # NetworkX API Compatibility Methods

    def add_node(self, node_for_adding, **attr):
        """Add a single node."""
        self._graph.add_node(node_for_adding, **attr)

        if not self._batch_mode:
            self._persistent_nodes[node_for_adding] = PersistentMapping(attr)
            self._mark_changed()

    def add_nodes_from(self, nodes_for_adding, **attr):
        """Add multiple nodes."""
        self._graph.add_nodes_from(nodes_for_adding, **attr)

        if not self._batch_mode:
            for node in nodes_for_adding:
                if isinstance(node, tuple):
                    node_id, attrs = node[0], node[1] if len(node) > 1 else {}
                    combined_attrs = {**attr, **attrs}
                else:
                    node_id, combined_attrs = node, attr

                self._persistent_nodes[node_id] = PersistentMapping(combined_attrs)

            self._mark_changed()

    def remove_node(self, node):
        """Remove a single node."""
        self._graph.remove_node(node)

        if not self._batch_mode:
            if node in self._persistent_nodes:
                del self._persistent_nodes[node]

            # Remove associated edges
            edges_to_remove = []
            for edge_key in self._persistent_edges:
                if isinstance(edge_key, tuple) and len(edge_key) >= 2:
                    if edge_key[0] == node or edge_key[1] == node:
                        edges_to_remove.append(edge_key)

            for edge_key in edges_to_remove:
                del self._persistent_edges[edge_key]

            self._mark_changed()

    def remove_nodes_from(self, nodes):
        """Remove multiple nodes."""
        self._graph.remove_nodes_from(nodes)

        if not self._batch_mode:
            for node in nodes:
                if node in self._persistent_nodes:
                    del self._persistent_nodes[node]

                # Remove associated edges
                edges_to_remove = []
                for edge_key in self._persistent_edges:
                    if isinstance(edge_key, tuple) and len(edge_key) >= 2:
                        if edge_key[0] == node or edge_key[1] == node:
                            edges_to_remove.append(edge_key)

                for edge_key in edges_to_remove:
                    del self._persistent_edges[edge_key]

            self._mark_changed()

    def add_edge(self, u_of_edge, v_of_edge, **attr):
        """Add a single edge."""
        self._graph.add_edge(u_of_edge, v_of_edge, **attr)

        if not self._batch_mode:
            if self._graph.is_multigraph():
                # Get the key for the edge that was just added
                keys = list(self._graph[u_of_edge][v_of_edge].keys())
                key = keys[-1]  # Last added key
                edge_key = (u_of_edge, v_of_edge, key)
            else:
                edge_key = (u_of_edge, v_of_edge)

            self._persistent_edges[edge_key] = PersistentMapping(attr)
            self._mark_changed()

    def add_edges_from(self, ebunch_to_add, **attr):
        """Add multiple edges."""
        self._graph.add_edges_from(ebunch_to_add, **attr)

        if not self._batch_mode:
            for edge in ebunch_to_add:
                if len(edge) == 2:
                    u, v = edge
                    edge_attrs = attr
                elif len(edge) == 3:
                    if self._graph.is_multigraph():
                        u, v, key = edge
                        edge_attrs = attr
                        edge_key = (u, v, key)
                    else:
                        u, v, edge_attrs = edge
                        edge_attrs = {**attr, **edge_attrs}
                        edge_key = (u, v)
                else:
                    u, v, key, edge_attrs = edge[:4]
                    edge_attrs = {**attr, **edge_attrs}
                    edge_key = (u, v, key) if self._graph.is_multigraph() else (u, v)

                if not self._graph.is_multigraph():
                    edge_key = (u, v)

                self._persistent_edges[edge_key] = PersistentMapping(edge_attrs)

            self._mark_changed()

    def remove_edge(self, u, v, key=None):
        """Remove a single edge."""
        if self._graph.is_multigraph() and key is not None:
            self._graph.remove_edge(u, v, key)
            edge_key = (u, v, key)
        else:
            self._graph.remove_edge(u, v)
            edge_key = (u, v)

        if not self._batch_mode:
            if edge_key in self._persistent_edges:
                del self._persistent_edges[edge_key]
            self._mark_changed()

    def remove_edges_from(self, ebunch):
        """Remove multiple edges."""
        self._graph.remove_edges_from(ebunch)

        if not self._batch_mode:
            for edge in ebunch:
                if len(edge) == 2:
                    u, v = edge
                    edge_key = (u, v)
                else:
                    u, v, key = edge[:3]
                    edge_key = (u, v, key) if self._graph.is_multigraph() else (u, v)

                if edge_key in self._persistent_edges:
                    del self._persistent_edges[edge_key]

            self._mark_changed()

    # Graph property delegation
    @property
    def nodes(self):
        """Return the nodes view."""
        return self._graph.nodes

    @property
    def edges(self):
        """Return the edges view."""
        return self._graph.edges

    @property
    def graph(self):
        """Return graph attributes."""
        return self._graph.graph

    @property
    def name(self):
        """Return the graph name."""
        return self._graph.name

    @name.setter
    def name(self, value):
        """Set the graph name."""
        self._graph.name = value
        self._mark_changed()

    # Graph information methods
    def number_of_nodes(self):
        """Return the number of nodes."""
        return self._graph.number_of_nodes()

    def number_of_edges(self):
        """Return the number of edges."""
        return self._graph.number_of_edges()

    def is_directed(self):
        """Return True if graph is directed."""
        return self._graph.is_directed()

    def is_multigraph(self):
        """Return True if graph is a multigraph."""
        return self._graph.is_multigraph()

    # Batch operations
    def start_batch_mode(self):
        """Start batch mode for bulk operations."""
        self._batch_mode = True
        self._pending_changes = []

    def end_batch_mode(self):
        """End batch mode and synchronize all changes."""
        self._batch_mode = False
        self._sync_to_persistent()
        self._pending_changes = []

    def __getattr__(self, name):
        """Delegate unknown attributes to the underlying NetworkX graph."""
        if hasattr(self._graph, name):
            attr = getattr(self._graph, name)
            if callable(attr):

                def wrapper(*args, **kwargs):
                    result = attr(*args, **kwargs)
                    # If the method might have modified the graph, sync changes
                    if not self._batch_mode and name in [
                        "clear",
                        "update",
                        "add_weighted_edges_from",
                        "remove_nodes_from",
                        "remove_edges_from",
                    ]:
                        self._sync_to_persistent()
                    return result

                return wrapper
            return attr
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    def copy(self, as_view=False):
        """Return a copy of the graph."""
        if as_view:
            return self._graph.copy(as_view=True)

        # Create a new persistent graph with the same data
        new_graph = PersistentNetworkXGraph(
            graph_type=self.graph_type,
            graph_id=f"{self.graph_id}_copy" if self.graph_id else None,
            graph_name=f"{self.graph_name}_copy" if self.graph_name else "",
            version=self.version,
        )

        # Copy all data
        new_graph._graph = self._graph.copy()
        new_graph._sync_to_persistent()

        return new_graph

    def to_networkx(self):
        """Return the underlying NetworkX graph."""
        return self._graph.copy()

    def save_to_pickle(self, path: str):
        """Save the graph to a pickle file."""
        with open(path, "wb") as f:
            pickle.dump(self._graph, f)

    @classmethod
    def load_from_pickle(cls, path: str, **kwargs):
        """Load a graph from a pickle file."""
        with open(path, "rb") as f:
            nx_graph = pickle.load(f)

        # Determine graph type
        graph_type = nx_graph.__class__.__name__

        # Create persistent graph
        persistent_graph = cls(graph_type=graph_type, **kwargs)
        persistent_graph._graph = nx_graph
        persistent_graph._sync_to_persistent()

        return persistent_graph

    @classmethod
    def from_networkx(cls, nx_graph, **kwargs):
        """Create a persistent graph from a NetworkX graph."""
        graph_type = nx_graph.__class__.__name__

        persistent_graph = cls(graph_type=graph_type, **kwargs)
        persistent_graph._graph = nx_graph.copy()
        persistent_graph._sync_to_persistent()

        return persistent_graph

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "graph_id": self.graph_id,
            "graph_name": self.graph_name,
            "graph_type": self.graph_type,
            "version": self.version,
            "number_of_nodes": self.number_of_nodes(),
            "number_of_edges": self.number_of_edges(),
            "is_directed": self.is_directed(),
            "is_multigraph": self.is_multigraph(),
            "is_connected": (
                nx.is_connected(self._graph)
                if not self.is_directed()
                else nx.is_weakly_connected(self._graph)
            ),
            "density": nx.density(self._graph),
            "persistent_nodes_count": len(self._persistent_nodes),
            "persistent_edges_count": len(self._persistent_edges),
        }

    def validate_integrity(self) -> Dict[str, Any]:
        """Validate the integrity of the persistent graph."""
        issues = []

        # Check node consistency
        nx_nodes = set(self._graph.nodes())
        persistent_nodes = set(self._persistent_nodes.keys())

        if nx_nodes != persistent_nodes:
            issues.append(
                f"Node mismatch: NetworkX has {len(nx_nodes)}, persistent has {len(persistent_nodes)}"
            )

        # Check edge consistency
        nx_edges = set(self._graph.edges())
        if self._graph.is_multigraph():
            nx_edges = set((u, v, k) for u, v, k in self._graph.edges(keys=True))

        persistent_edges = set(self._persistent_edges.keys())

        if nx_edges != persistent_edges:
            issues.append(
                f"Edge mismatch: NetworkX has {len(nx_edges)}, persistent has {len(persistent_edges)}"
            )

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "statistics": self.get_statistics(),
        }

    def __repr__(self):
        """String representation of the graph."""
        return f"PersistentNetworkXGraph({self.graph_type}, nodes={len(self.nodes)}, edges={len(self.edges)})"

    def __str__(self):
        """Human-readable string representation."""
        name_part = f" '{self.graph_name}'" if self.graph_name else ""
        return f"{self.graph_type}{name_part} with {len(self.nodes)} nodes and {len(self.edges)} edges"
