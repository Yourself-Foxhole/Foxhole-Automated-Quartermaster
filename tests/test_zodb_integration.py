"""
Test suite for ZODB integration functionality.

Comprehensive tests covering ZODB functionality, transaction management,
persistent node operations, graph storage, and migration utilities.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import networkx as nx

from services.storage.graph_storage import GraphStorage
from services.storage.migration_manager import GraphMigrationManager
from services.storage.nodes import (
    PersistentBaseNode,
    PersistentInventoryNode,
    PersistentProductionNode,
    PersistentTaskNode,
)
from services.storage.persistent_graph_service import PersistentGraphService
from services.storage.persistent_networkx_graph import PersistentNetworkXGraph
from services.storage.zodb_manager import ZODBManager


class TestZODBManager(unittest.TestCase):
    """Test ZODB Manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.zodb_manager = ZODBManager(self.db_path)

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            self.zodb_manager.close()
        except:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Reset singleton
        ZODBManager.reset_instance()

    def test_singleton_pattern(self):
        """Test that ZODBManager follows singleton pattern."""
        manager1 = ZODBManager(self.db_path)
        manager2 = ZODBManager(self.db_path)
        self.assertIs(manager1, manager2)

    def test_database_creation(self):
        """Test database file creation."""
        self.assertTrue(os.path.exists(self.db_path))

    def test_transaction_context_manager(self):
        """Test transaction context manager."""
        with self.zodb_manager.transaction() as root:
            root["test_key"] = "test_value"

        # Verify data was stored
        with self.zodb_manager.read_only_transaction() as root:
            self.assertEqual(root["test_key"], "test_value")

    def test_transaction_rollback_on_error(self):
        """Test that transactions roll back on errors."""
        try:
            with self.zodb_manager.transaction() as root:
                root["test_key"] = "test_value"
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify data was not stored
        with self.zodb_manager.read_only_transaction() as root:
            self.assertNotIn("test_key", root)

    def test_health_check(self):
        """Test health check functionality."""
        health = self.zodb_manager.health_check()
        self.assertIn("status", health)
        self.assertIn("issues", health)
        self.assertEqual(health["status"], "healthy")

    def test_get_statistics(self):
        """Test statistics collection."""
        stats = self.zodb_manager.get_statistics()
        self.assertIn("db_size_bytes", stats)
        self.assertIn("cache_size", stats)


class TestGraphStorage(unittest.TestCase):
    """Test GraphStorage container functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.storage = GraphStorage()

    def test_initialization(self):
        """Test GraphStorage initialization."""
        self.assertEqual(len(self.storage.graph_registry), 0)
        self.assertIn("graph_types", self.storage.metadata)

    def test_register_graph(self):
        """Test graph registration."""
        mock_graph = MagicMock()

        self.storage.register_graph(
            "test_graph", "production", mock_graph, {"test": "metadata"}
        )

        self.assertIn("test_graph", self.storage.graph_registry)
        self.assertEqual(self.storage.production_graphs["test_graph"], mock_graph)

    def test_get_graph(self):
        """Test graph retrieval."""
        mock_graph = MagicMock()
        self.storage.register_graph("test_graph", "production", mock_graph)

        retrieved_graph = self.storage.get_graph("test_graph")
        self.assertEqual(retrieved_graph, mock_graph)

    def test_remove_graph(self):
        """Test graph removal."""
        mock_graph = MagicMock()
        self.storage.register_graph("test_graph", "production", mock_graph)

        success = self.storage.remove_graph("test_graph")
        self.assertTrue(success)
        self.assertNotIn("test_graph", self.storage.graph_registry)

    def test_list_graphs_by_type(self):
        """Test listing graphs by type."""
        mock_graph1 = MagicMock()
        mock_graph2 = MagicMock()

        self.storage.register_graph("prod_graph", "production", mock_graph1)
        self.storage.register_graph("task_graph", "task", mock_graph2)

        prod_graphs = self.storage.list_graphs("production")
        task_graphs = self.storage.list_graphs("task")

        self.assertEqual(prod_graphs, ["prod_graph"])
        self.assertEqual(task_graphs, ["task_graph"])

    def test_validate_integrity(self):
        """Test storage integrity validation."""
        mock_graph = MagicMock()
        self.storage.register_graph("test_graph", "production", mock_graph)

        validation = self.storage.validate_integrity()
        self.assertTrue(validation["is_valid"])
        self.assertEqual(len(validation["issues"]), 0)


class TestPersistentNodes(unittest.TestCase):
    """Test persistent node classes."""

    def test_base_node_creation(self):
        """Test PersistentBaseNode creation."""
        node = PersistentBaseNode(name="Test Node", node_type="test")

        self.assertEqual(node.name, "Test Node")
        self.assertEqual(node.node_type, "test")
        self.assertTrue(node.is_active)
        self.assertIsNotNone(node.node_id)

    def test_base_node_attributes(self):
        """Test base node attribute management."""
        node = PersistentBaseNode(name="Test Node")

        node.set_attribute("test_attr", "test_value")
        self.assertEqual(node.get_attribute("test_attr"), "test_value")

        success = node.remove_attribute("test_attr")
        self.assertTrue(success)
        self.assertIsNone(node.get_attribute("test_attr"))

    def test_base_node_tags(self):
        """Test base node tag management."""
        node = PersistentBaseNode(name="Test Node")

        node.add_tag("important")
        self.assertTrue(node.has_tag("important"))

        success = node.remove_tag("important")
        self.assertTrue(success)
        self.assertFalse(node.has_tag("important"))

    def test_inventory_node_inventory_management(self):
        """Test inventory node inventory operations."""
        node = PersistentInventoryNode(
            name="Test Storage", location="Test Location", max_capacity=1000
        )

        # Test adding inventory
        success = node.add_inventory("bmats", 100)
        self.assertTrue(success)

        inventory = node.get_current_inventory("bmats")
        self.assertEqual(inventory["bmats:standard"], 100)

        # Test removing inventory
        success = node.remove_inventory("bmats", 50)
        self.assertTrue(success)

        available = node.get_available_inventory("bmats")
        self.assertEqual(available, 50)

    def test_inventory_node_reservations(self):
        """Test inventory node reservation system."""
        node = PersistentInventoryNode(name="Test Storage", max_capacity=1000)

        node.add_inventory("bmats", 100)

        # Test reservation
        success = node.reserve_inventory("bmats", 30, "order_123")
        self.assertTrue(success)

        available = node.get_available_inventory("bmats")
        self.assertEqual(available, 70)

        # Test reservation release
        success = node.release_reservation("bmats", "order_123")
        self.assertTrue(success)

        available = node.get_available_inventory("bmats")
        self.assertEqual(available, 100)

    def test_production_node_recipe_management(self):
        """Test production node recipe operations."""
        node = PersistentProductionNode(name="Test Factory", facility_type="factory")

        # Add recipe
        recipe_id = node.add_recipe(
            {"inputs": {"bmats": 20}, "outputs": {"rifle": 1}, "cycle_time": 60}
        )

        self.assertIsNotNone(recipe_id)

        # Get recipe
        recipe = node.get_recipe(recipe_id)
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["inputs"]["bmats"], 20)

        # Remove recipe
        success = node.remove_recipe(recipe_id)
        self.assertTrue(success)

        recipe = node.get_recipe(recipe_id)
        self.assertIsNone(recipe)

    def test_production_node_production_operations(self):
        """Test production node production management."""
        node = PersistentProductionNode(name="Test Factory")

        # Add materials and recipe
        node.add_input_material("bmats", 100)

        recipe_id = node.add_recipe(
            {"inputs": {"bmats": 20}, "outputs": {"rifle": 1}, "cycle_time": 60}
        )

        # Start production
        success = node.start_production(recipe_id, cycles=2)
        self.assertTrue(success)

        # Check active recipes
        self.assertIn(recipe_id, node.active_recipes)

        # Complete a cycle
        success = node.complete_production_cycle(recipe_id)
        self.assertTrue(success)

        # Check output storage
        self.assertIn("rifle", node.output_storage)

    def test_task_node_lifecycle(self):
        """Test task node lifecycle management."""
        node = PersistentTaskNode(name="Test Task", task_type="logistics")

        # Start task
        success = node.start_task()
        self.assertTrue(success)
        self.assertEqual(node.task_status, "active")

        # Update progress
        success = node.update_progress(50, "Half complete")
        self.assertTrue(success)
        self.assertEqual(node.progress_percentage, 50)

        # Complete task
        success = node.complete_task(success=True, results={"output": "test"})
        self.assertTrue(success)
        self.assertEqual(node.task_status, "completed")
        self.assertEqual(node.results["output"], "test")

    def test_task_node_dependencies(self):
        """Test task node dependency management."""
        node = PersistentTaskNode(name="Test Task")

        # Add dependency
        success = node.add_dependency("task_123", "blocks")
        self.assertTrue(success)

        self.assertEqual(len(node.dependencies), 1)
        self.assertEqual(node.dependencies[0]["task_id"], "task_123")

        # Remove dependency
        success = node.remove_dependency("task_123")
        self.assertTrue(success)
        self.assertEqual(len(node.dependencies), 0)


class TestPersistentNetworkXGraph(unittest.TestCase):
    """Test PersistentNetworkXGraph functionality."""

    def test_graph_creation(self):
        """Test persistent graph creation."""
        graph = PersistentNetworkXGraph(
            graph_type="DiGraph", graph_id="test_graph", graph_name="Test Graph"
        )

        self.assertEqual(graph.graph_id, "test_graph")
        self.assertEqual(graph.graph_name, "Test Graph")
        self.assertEqual(graph.graph_type, "DiGraph")
        self.assertTrue(graph.is_directed())

    def test_node_operations(self):
        """Test node addition and removal."""
        graph = PersistentNetworkXGraph(graph_type="DiGraph")

        # Add nodes
        graph.add_node("A", weight=1)
        graph.add_node("B", weight=2)

        self.assertEqual(len(graph.nodes), 2)
        self.assertIn("A", graph.nodes)
        self.assertIn("B", graph.nodes)

        # Remove node
        graph.remove_node("A")
        self.assertEqual(len(graph.nodes), 1)
        self.assertNotIn("A", graph.nodes)

    def test_edge_operations(self):
        """Test edge addition and removal."""
        graph = PersistentNetworkXGraph(graph_type="DiGraph")

        # Add nodes and edges
        graph.add_node("A")
        graph.add_node("B")
        graph.add_edge("A", "B", weight=5)

        self.assertEqual(len(graph.edges), 1)
        self.assertIn(("A", "B"), graph.edges)

        # Remove edge
        graph.remove_edge("A", "B")
        self.assertEqual(len(graph.edges), 0)

    def test_batch_operations(self):
        """Test batch mode operations."""
        graph = PersistentNetworkXGraph(graph_type="DiGraph")

        graph.start_batch_mode()

        # Add multiple nodes and edges
        graph.add_nodes_from(["A", "B", "C"])
        graph.add_edges_from([("A", "B"), ("B", "C")])

        graph.end_batch_mode()

        self.assertEqual(len(graph.nodes), 3)
        self.assertEqual(len(graph.edges), 2)

    def test_networkx_compatibility(self):
        """Test NetworkX API compatibility."""
        graph = PersistentNetworkXGraph(graph_type="DiGraph")

        # Add data
        graph.add_nodes_from(["A", "B", "C"])
        graph.add_edges_from([("A", "B"), ("B", "C")])

        # Test NetworkX methods work
        self.assertEqual(graph.number_of_nodes(), 3)
        self.assertEqual(graph.number_of_edges(), 2)

        # Test that we can use NetworkX algorithms
        nx_graph = graph.to_networkx()
        self.assertTrue(nx.is_directed_acyclic_graph(nx_graph))

    def test_copy_operations(self):
        """Test graph copying."""
        graph = PersistentNetworkXGraph(
            graph_type="DiGraph", graph_id="original", graph_name="Original Graph"
        )

        graph.add_nodes_from(["A", "B"])
        graph.add_edge("A", "B")

        # Test copy
        copy_graph = graph.copy()

        self.assertEqual(len(copy_graph.nodes), 2)
        self.assertEqual(len(copy_graph.edges), 1)
        self.assertNotEqual(copy_graph.graph_id, graph.graph_id)


class TestPersistentGraphService(unittest.TestCase):
    """Test PersistentGraphService functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_service.db")

        # Mock the global zodb_manager
        self.mock_zodb = ZODBManager(self.db_path)

        self.service = PersistentGraphService()
        self.service.zodb_manager = self.mock_zodb

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            self.mock_zodb.close()
        except:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        ZODBManager.reset_instance()

    def test_graph_creation_and_retrieval(self):
        """Test graph creation and retrieval through service."""
        # Create graph
        graph = self.service.create_graph(
            graph_id="test_graph", graph_type="DiGraph", graph_name="Test Graph"
        )

        self.assertIsInstance(graph, PersistentNetworkXGraph)
        self.assertEqual(graph.graph_id, "test_graph")

        # Retrieve graph
        retrieved_graph = self.service.get_graph("test_graph")
        self.assertIsNotNone(retrieved_graph)
        self.assertEqual(retrieved_graph.graph_id, "test_graph")

    def test_graph_existence_check(self):
        """Test graph existence checking."""
        # Check non-existent graph
        self.assertFalse(self.service.graph_exists("nonexistent"))

        # Create and check existing graph
        self.service.create_graph("test_graph")
        self.assertTrue(self.service.graph_exists("test_graph"))

    def test_graph_listing(self):
        """Test graph listing functionality."""
        # Create multiple graphs
        self.service.create_graph("graph1", metadata={"type": "production"})
        self.service.create_graph("graph2", metadata={"type": "task"})

        # List all graphs
        all_graphs = self.service.list_graphs()
        self.assertEqual(len(all_graphs), 2)
        self.assertIn("graph1", all_graphs)
        self.assertIn("graph2", all_graphs)

    def test_node_creation_and_management(self):
        """Test node creation through service."""
        # Create graph first
        graph_id = "test_graph"
        self.service.create_graph(graph_id)

        # Create node
        node = self.service.create_node(
            graph_id=graph_id,
            node_type="inventory",
            name="Test Storage",
            location="Test Location",
        )

        self.assertIsInstance(node, PersistentInventoryNode)
        self.assertEqual(node.name, "Test Storage")

        # Retrieve node
        retrieved_node = self.service.get_node(graph_id, node.node_id)
        self.assertIsNotNone(retrieved_node)
        self.assertEqual(retrieved_node.node_id, node.node_id)

    def test_batch_operations(self):
        """Test batch operations through service."""
        graph_id = "test_graph"
        self.service.create_graph(graph_id)

        # Perform batch operations
        with self.service.batch_operation(graph_id) as graph:
            graph.add_nodes_from(["A", "B", "C"])
            graph.add_edges_from([("A", "B"), ("B", "C")])

        # Verify results
        graph = self.service.get_graph(graph_id)
        self.assertEqual(len(graph.nodes), 3)
        self.assertEqual(len(graph.edges), 2)

    def test_service_caching(self):
        """Test service caching functionality."""
        # Create graph
        graph_id = "test_graph"
        self.service.create_graph(graph_id)

        # First access (cache miss)
        graph1 = self.service.get_graph(graph_id)

        # Second access (should be cache hit)
        graph2 = self.service.get_graph(graph_id)

        # Check cache statistics
        stats = self.service.get_service_statistics()
        self.assertGreater(stats["cache_hit_rate_percent"], 0)

    def test_health_check(self):
        """Test service health check."""
        health = self.service.health_check()

        self.assertIn("status", health)
        self.assertIn("issues", health)
        self.assertIn("timestamp", health)


class TestGraphMigrationManager(unittest.TestCase):
    """Test GraphMigrationManager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.migration_manager = GraphMigrationManager(
            backup_dir=os.path.join(self.temp_dir, "backups")
        )

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_migration_session_management(self):
        """Test migration session lifecycle."""
        migration_id = self.migration_manager.start_migration("Test Migration")

        self.assertIsNotNone(migration_id)
        self.assertEqual(self.migration_manager.current_migration_id, migration_id)

        # Test logging
        self.migration_manager.log_migration("Test message")
        self.assertEqual(
            len(self.migration_manager.migration_log), 2
        )  # start + test message

    def test_migration_status(self):
        """Test migration status reporting."""
        self.migration_manager.start_migration("Test Migration")
        self.migration_manager.log_migration("Test message", "info")
        self.migration_manager.log_migration("Warning message", "warning")
        self.migration_manager.log_migration("Error message", "error")

        status = self.migration_manager.get_migration_status()

        self.assertEqual(status["log_entries_count"], 4)  # start + 3 messages
        self.assertEqual(status["errors_count"], 1)
        self.assertEqual(status["warnings_count"], 1)

    def test_migration_report_export(self):
        """Test migration report export."""
        self.migration_manager.start_migration("Test Migration")
        self.migration_manager.log_migration("Test message")

        report_path = self.migration_manager.export_migration_report()

        self.assertTrue(os.path.exists(report_path))

        # Verify report content
        import json

        with open(report_path, "r") as f:
            report = json.load(f)

        self.assertIn("migration_id", report)
        self.assertIn("log_entries", report)
        self.assertIn("summary", report)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete ZODB system."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "integration_test.db")

        # Create fresh ZODB manager
        self.zodb_manager = ZODBManager(self.db_path)

        # Create service with mock manager
        self.service = PersistentGraphService()
        self.service.zodb_manager = self.zodb_manager

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            self.zodb_manager.close()
        except:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        ZODBManager.reset_instance()

    def test_complete_workflow(self):
        """Test complete workflow from graph creation to complex operations."""
        # Create a production graph
        graph_id = "foxhole_production"
        graph = self.service.create_graph(
            graph_id=graph_id,
            graph_type="DiGraph",
            graph_name="Foxhole Production Network",
            metadata={"game": "foxhole", "type": "production"},
        )

        # Create production nodes
        salvage_node = self.service.create_node(
            graph_id=graph_id,
            node_type="production",
            name="Salvage Mine",
            facility_type="resource",
            location="Deadlands",
        )

        refinery_node = self.service.create_node(
            graph_id=graph_id,
            node_type="production",
            name="Basic Refinery",
            facility_type="refinery",
            location="Loch Mor",
        )

        # Add recipes
        bmat_recipe = {
            "inputs": {"Salvage": 20},
            "outputs": {"Basic Materials": 1},
            "cycle_time": 60,
        }
        refinery_node.add_recipe(bmat_recipe)

        # Create graph connections
        graph.add_edge(
            salvage_node.node_id, refinery_node.node_id, material="Salvage", quantity=20
        )

        # Create inventory nodes
        storage_node = self.service.create_node(
            graph_id=graph_id,
            node_type="inventory",
            name="Main Storage",
            location="Loch Mor",
            max_capacity=10000,
        )

        # Add inventory
        storage_node.add_inventory("Basic Materials", 500)
        storage_node.add_inventory("Salvage", 1000)

        # Create task for logistics
        task_node = self.service.create_node(
            graph_id=graph_id,
            node_type="task",
            name="Transport Salvage",
            task_type="logistics",
            description="Transport salvage from mine to refinery",
        )

        # Start and complete task
        task_node.start_task()
        task_node.update_progress(100, "Transport completed")

        # Verify the complete system
        retrieved_graph = self.service.get_graph(graph_id)
        self.assertEqual(len(retrieved_graph.nodes), 4)  # 3 facility nodes + storage
        self.assertEqual(len(retrieved_graph.edges), 1)

        # Test complex operations
        with self.service.batch_operation(graph_id) as batch_graph:
            # Add more nodes in batch
            for i in range(10):
                batch_graph.add_node(f"resource_{i}", type="resource")

        # Verify batch operation results
        retrieved_graph = self.service.get_graph(graph_id)
        self.assertEqual(len(retrieved_graph.nodes), 14)  # 4 + 10 batch nodes

        # Test persistence across transactions
        with self.zodb_manager.transaction() as root:
            storage = root["graph_storage"]
            self.assertEqual(len(storage.list_graphs()), 1)

        # Test service statistics
        stats = self.service.get_service_statistics()
        self.assertGreater(stats["total_operations"], 0)


if __name__ == "__main__":
    unittest.main()
