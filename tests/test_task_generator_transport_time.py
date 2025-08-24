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
        self.source = InventoryNode("source", "Supply Depot", base_type=BaseType.ITEM_NODE)
        self.target = InventoryNode("target", "Frontline Base", base_type=BaseType.ITEM_NODE)
        
        # Set up inventory and demand
        self.source.inventory = {"rifle": 50}
        self.target.delta = {"rifle": 20}
        
        self.graph.add_node(self.source)
        self.graph.add_node(self.target)

    def test_task_generation_without_transport_time(self):
        """Test task generation without transport_time on edge."""
        # Add edge without transport_time for transportation tasks
        # Note: TaskGenerator looks for edges FROM the target node to find sources
        self.graph.add_edge("target", "source", allowed_items=["rifle"])
        
        task_gen = TaskGenerator([self.source, self.target])
        tasks = task_gen.get_actionable_tasks()
        
        # Should generate tasks even without transport_time
        self.assertGreater(len(tasks), 0)
        
        # Find transportation task
        transport_tasks = [t for t in tasks if hasattr(t, 'source') and t.task_type == 'transportation']
        self.assertGreater(len(transport_tasks), 0)
        
        transport_task = transport_tasks[0]
        self.assertNotIn("transport_time", transport_task.priority.signals)

    def test_task_generation_with_transport_time(self):
        """Test task generation with transport_time on edge."""
        transport_time = 2.5
        
        # Add edge with transport_time for transportation tasks
        self.graph.add_edge("target", "source", allowed_items=["rifle"], transport_time=transport_time)
        
        task_gen = TaskGenerator([self.source, self.target])
        tasks = task_gen.get_actionable_tasks()
        
        # Find transportation task
        transport_tasks = [t for t in tasks if hasattr(t, 'source') and t.task_type == 'transportation']
        self.assertGreater(len(transport_tasks), 0)
        
        transport_task = transport_tasks[0]
        
        # Verify transport_time is included in priority signals
        self.assertIn("transport_time", transport_task.priority.signals)
        self.assertEqual(transport_task.priority.signals["transport_time"], transport_time)

    def test_multiple_edges_different_transport_times(self):
        """Test TaskGenerator handles multiple edges with different transport times."""
        # Add another source with different transport time
        source2 = InventoryNode("source2", "Secondary Depot", base_type=BaseType.ITEM_NODE)
        source2.inventory = {"rifle": 30}
        self.graph.add_node(source2)
        
        # Add edges with different transport times
        self.graph.add_edge("target", "source", allowed_items=["rifle"], transport_time=1.0)  # Fast
        self.graph.add_edge("target", "source2", allowed_items=["rifle"], transport_time=5.0)  # Slow
        
        task_gen = TaskGenerator([self.source, source2, self.target])
        tasks = task_gen.get_actionable_tasks()
        
        # Find transportation tasks
        transport_tasks = [t for t in tasks if hasattr(t, 'source') and t.task_type == 'transportation']
        self.assertEqual(len(transport_tasks), 2)
        
        # Verify both tasks have transport_time in signals
        for task in transport_tasks:
            self.assertIn("transport_time", task.priority.signals)
        
        # Find tasks by source
        fast_task = next(t for t in transport_tasks if t.source.node_id == "source")
        slow_task = next(t for t in transport_tasks if t.source.node_id == "source2")
        
        self.assertEqual(fast_task.priority.signals["transport_time"], 1.0)
        self.assertEqual(slow_task.priority.signals["transport_time"], 5.0)
        
        # Fast transport should have higher priority (due to negative weight)
        self.assertGreater(fast_task.priority.score, slow_task.priority.score)

    def test_production_tasks_unaffected_by_transport_time(self):
        """Test that production tasks are not affected by transport_time."""
        # Set up production node
        factory = InventoryNode("factory", "Production Factory", base_type=BaseType.PRODUCTION)
        factory.delta = {"rifle": 10}
        self.graph.add_node(factory)
        
        # Add edge with transport_time (shouldn't affect production tasks)
        self.graph.add_edge("factory", "target", allowed_items=["rifle"], transport_time=3.0)
        
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
        # Add another source without transport_time
        source2 = InventoryNode("source2", "Legacy Depot", base_type=BaseType.ITEM_NODE)
        source2.inventory = {"rifle": 25}
        self.graph.add_node(source2)
        
        # Add edges - one with transport_time, one without
        self.graph.add_edge("target", "source", allowed_items=["rifle"], transport_time=2.0)
        self.graph.add_edge("target", "source2", allowed_items=["rifle"])  # No transport_time
        
        task_gen = TaskGenerator([self.source, source2, self.target])
        tasks = task_gen.get_actionable_tasks()
        
        # Find transportation tasks
        transport_tasks = [t for t in tasks if hasattr(t, 'source') and t.task_type == 'transportation']
        self.assertEqual(len(transport_tasks), 2)
        
        # Find tasks by source
        timed_task = next(t for t in transport_tasks if t.source.node_id == "source")
        untimed_task = next(t for t in transport_tasks if t.source.node_id == "source2")
        
        # Verify only one has transport_time
        self.assertIn("transport_time", timed_task.priority.signals)
        self.assertNotIn("transport_time", untimed_task.priority.signals)
        
        self.assertEqual(timed_task.priority.signals["transport_time"], 2.0)

    def test_zero_transport_time(self):
        """Test edge with zero transport_time."""
        # Add edge with zero transport_time
        self.graph.add_edge("target", "source", allowed_items=["rifle"], transport_time=0.0)
        
        task_gen = TaskGenerator([self.source, self.target])
        tasks = task_gen.get_actionable_tasks()
        
        # Find transportation task
        transport_tasks = [t for t in tasks if hasattr(t, 'source') and t.task_type == 'transportation']
        self.assertGreater(len(transport_tasks), 0)
        
        transport_task = transport_tasks[0]
        
        # Verify zero transport_time is included
        self.assertIn("transport_time", transport_task.priority.signals)
        self.assertEqual(transport_task.priority.signals["transport_time"], 0.0)


if __name__ == "__main__":
    unittest.main()