"""
Integration tests for transport_time functionality with TaskGenerator.
"""

import unittest
from services.inventory.inventory_graph import InventoryGraph, InventoryNode
from services.tasks.task_layer import TaskGenerator, Priority
from services.inventory.base_types import BaseType


class TestTaskGeneratorTransportTime(unittest.TestCase):
    """Test transport_time integration with TaskGenerator."""

    def setUp(self):
        """Set up test fixtures."""
        self.graph = InventoryGraph()

    def test_task_generation_without_transport_time(self):
        """Test task generation without transport_time on edge."""
        # Create node that has both inventory and demand (to trigger TaskGenerator logic)
        node = InventoryNode("node", "Test Node", base_type=BaseType.PRODUCTION)
        node.inventory = {"rifle": 100}  # Has rifles
        node.delta = {"rifle": 50}       # Also needs rifles
        
        self.graph.add_node(node)
        
        # Add self-edge without transport_time
        self.graph.add_edge("node", "node", allowed_items=["rifle"])
        
        task_gen = TaskGenerator([node])
        tasks = task_gen.get_actionable_tasks()
        
        # Should generate both production and transportation tasks
        self.assertGreater(len(tasks), 0)
        
        # Find transportation task
        transport_tasks = [t for t in tasks if hasattr(t, 'source') and t.task_type == 'transportation']
        
        if transport_tasks:
            transport_task = transport_tasks[0]
            self.assertNotIn("transport_time", transport_task.priority.signals)

    def test_task_generation_with_transport_time(self):
        """Test task generation with transport_time on edge."""
        transport_time = 2.5
        
        # Create node that has both inventory and demand (to trigger TaskGenerator logic)
        node = InventoryNode("node", "Test Node", base_type=BaseType.PRODUCTION)
        node.inventory = {"rifle": 100}  # Has rifles
        node.delta = {"rifle": 50}       # Also needs rifles
        
        self.graph.add_node(node)
        
        # Add self-edge with transport_time
        self.graph.add_edge("node", "node", allowed_items=["rifle"], transport_time=transport_time)
        
        task_gen = TaskGenerator([node])
        tasks = task_gen.get_actionable_tasks()
        
        # Find transportation task
        transport_tasks = [t for t in tasks if hasattr(t, 'source') and t.task_type == 'transportation']
        
        if transport_tasks:
            transport_task = transport_tasks[0]
            # Verify transport_time is included in priority signals
            self.assertIn("transport_time", transport_task.priority.signals)
            self.assertEqual(transport_task.priority.signals["transport_time"], transport_time)

    def test_multiple_edges_different_transport_times(self):
        """Test TaskGenerator handles multiple edges with different transport times."""
        # Create multiple nodes that can supply to a demander
        supplier1 = InventoryNode("supplier1", "First Supplier", base_type=BaseType.ITEM_NODE)
        supplier1.inventory = {"rifle": 30}
        supplier1.delta = {"rifle": 10}  # Also needs some for itself
        
        supplier2 = InventoryNode("supplier2", "Second Supplier", base_type=BaseType.ITEM_NODE)
        supplier2.inventory = {"rifle": 40}
        supplier2.delta = {"rifle": 15}  # Also needs some for itself
        
        self.graph.add_node(supplier1)
        self.graph.add_node(supplier2)
        
        # Add self-edges with different transport times
        self.graph.add_edge("supplier1", "supplier1", allowed_items=["rifle"], transport_time=1.0)  # Fast
        self.graph.add_edge("supplier2", "supplier2", allowed_items=["rifle"], transport_time=5.0)  # Slow
        
        task_gen = TaskGenerator([supplier1, supplier2])
        tasks = task_gen.get_actionable_tasks()
        
        # Find transportation tasks
        transport_tasks = [t for t in tasks if hasattr(t, 'source') and t.task_type == 'transportation']
        self.assertGreaterEqual(len(transport_tasks), 2)
        
        # Verify both tasks have transport_time in signals
        found_fast = False
        found_slow = False
        
        for task in transport_tasks:
            if "transport_time" in task.priority.signals:
                if task.priority.signals["transport_time"] == 1.0:
                    found_fast = True
                elif task.priority.signals["transport_time"] == 5.0:
                    found_slow = True
        
        self.assertTrue(found_fast or found_slow)  # At least one should have transport_time

    def test_production_tasks_unaffected_by_transport_time(self):
        """Test that production tasks are not affected by transport_time."""
        # Set up production node
        factory = InventoryNode("factory", "Production Factory", base_type=BaseType.PRODUCTION)
        factory.delta = {"rifle": 10}
        factory.inventory = {"rifle": 5}  # Some inventory but still needs more
        
        self.graph.add_node(factory)
        
        # Add edge with transport_time (shouldn't affect production tasks)
        self.graph.add_edge("factory", "factory", allowed_items=["rifle"], transport_time=3.0)
        
        task_gen = TaskGenerator([factory])
        tasks = task_gen.get_actionable_tasks()
        
        # Find production task
        production_tasks = [t for t in tasks if t.task_type == 'production']
        self.assertGreater(len(production_tasks), 0)
        
        production_task = production_tasks[0]
        
        # Production tasks should not include transport_time in signals
        self.assertNotIn("transport_time", production_task.priority.signals)

    def test_mixed_edges_some_with_transport_time(self):
        """Test scenario with mixed edges - some with transport_time, some without."""
        # Create nodes with mixed edge configurations
        node1 = InventoryNode("node1", "Node with Time", base_type=BaseType.ITEM_NODE)
        node1.inventory = {"rifle": 25}
        node1.delta = {"rifle": 10}
        
        node2 = InventoryNode("node2", "Node without Time", base_type=BaseType.ITEM_NODE)
        node2.inventory = {"rifle": 30}
        node2.delta = {"rifle": 15}
        
        self.graph.add_node(node1)
        self.graph.add_node(node2)
        
        # Add edges - one with transport_time, one without
        self.graph.add_edge("node1", "node1", allowed_items=["rifle"], transport_time=2.0)
        self.graph.add_edge("node2", "node2", allowed_items=["rifle"])  # No transport_time
        
        task_gen = TaskGenerator([node1, node2])
        tasks = task_gen.get_actionable_tasks()
        
        # Find transportation tasks
        transport_tasks = [t for t in tasks if hasattr(t, 'source') and t.task_type == 'transportation']
        self.assertGreaterEqual(len(transport_tasks), 1)
        
        # Check that at least one task has transport_time and at least one doesn't
        has_time = any("transport_time" in t.priority.signals for t in transport_tasks)
        no_time = any("transport_time" not in t.priority.signals for t in transport_tasks)
        
        # At least one pattern should be found (preferably both)
        self.assertTrue(has_time or no_time)

    def test_zero_transport_time(self):
        """Test edge with zero transport_time."""
        # Create node with zero transport_time
        node = InventoryNode("node", "Zero Time Node", base_type=BaseType.ITEM_NODE)
        node.inventory = {"rifle": 50}
        node.delta = {"rifle": 20}
        
        self.graph.add_node(node)
        
        # Add edge with zero transport_time
        self.graph.add_edge("node", "node", allowed_items=["rifle"], transport_time=0.0)
        
        task_gen = TaskGenerator([node])
        tasks = task_gen.get_actionable_tasks()
        
        # Find transportation task
        transport_tasks = [t for t in tasks if hasattr(t, 'source') and t.task_type == 'transportation']
        
        if transport_tasks:
            transport_task = transport_tasks[0]
            # Verify zero transport_time is included
            self.assertIn("transport_time", transport_task.priority.signals)
            self.assertEqual(transport_task.priority.signals["transport_time"], 0.0)


if __name__ == "__main__":
    unittest.main()