"""
Unit tests for transport_time functionality in InventoryGraph.
"""

import unittest
from services.inventory.inventory_graph import InventoryGraph, InventoryNode, InventoryEdge


class TestTransportTime(unittest.TestCase):
    """Test transport_time attribute functionality on InventoryEdge."""

    def setUp(self):
        """Set up test fixtures."""
        self.graph = InventoryGraph()
        self.node1 = InventoryNode("n1", "Node 1")
        self.node2 = InventoryNode("n2", "Node 2")
        self.graph.add_node(self.node1)
        self.graph.add_node(self.node2)

    def test_edge_without_transport_time(self):
        """Test edge creation without transport_time."""
        self.graph.add_edge("n1", "n2", allowed_items=["rifle"])
        edge = self.graph.edges[0]
        
        self.assertIsNone(edge.get_transport_time())
        self.assertFalse(edge.has_transport_time())

    def test_edge_with_transport_time(self):
        """Test edge creation with transport_time."""
        transport_time = 2.5
        self.graph.add_edge("n1", "n2", allowed_items=["rifle"], transport_time=transport_time)
        edge = self.graph.edges[0]
        
        self.assertEqual(edge.get_transport_time(), transport_time)
        self.assertTrue(edge.has_transport_time())

    def test_set_transport_time_after_creation(self):
        """Test setting transport_time after edge creation."""
        self.graph.add_edge("n1", "n2", allowed_items=["rifle"])
        edge = self.graph.edges[0]
        
        # Initially no transport time
        self.assertIsNone(edge.get_transport_time())
        self.assertFalse(edge.has_transport_time())
        
        # Set transport time
        transport_time = 1.5
        edge.set_transport_time(transport_time)
        
        self.assertEqual(edge.get_transport_time(), transport_time)
        self.assertTrue(edge.has_transport_time())

    def test_clear_transport_time(self):
        """Test clearing transport_time by setting to None."""
        transport_time = 3.0
        self.graph.add_edge("n1", "n2", allowed_items=["rifle"], transport_time=transport_time)
        edge = self.graph.edges[0]
        
        # Initially has transport time
        self.assertEqual(edge.get_transport_time(), transport_time)
        self.assertTrue(edge.has_transport_time())
        
        # Clear transport time
        edge.set_transport_time(None)
        
        self.assertIsNone(edge.get_transport_time())
        self.assertFalse(edge.has_transport_time())

    def test_edge_constructor_with_transport_time(self):
        """Test direct InventoryEdge constructor with transport_time."""
        transport_time = 4.0
        edge = InventoryEdge(
            source=self.node1,
            target=self.node2,
            allowed_items=["ammo"],
            transport_time=transport_time
        )
        
        self.assertEqual(edge.get_transport_time(), transport_time)
        self.assertTrue(edge.has_transport_time())

    def test_backward_compatibility(self):
        """Test that existing code without transport_time still works."""
        # This should work without any issues
        edge = InventoryEdge(
            source=self.node1,
            target=self.node2,
            allowed_items=["rifle"],
            production_process="assemble_rifle"
        )
        
        self.assertIsNone(edge.get_transport_time())
        self.assertFalse(edge.has_transport_time())
        self.assertEqual(edge.allowed_items, ["rifle"])
        self.assertEqual(edge.production_process, "assemble_rifle")

    def test_zero_transport_time(self):
        """Test edge with zero transport_time."""
        transport_time = 0.0
        self.graph.add_edge("n1", "n2", allowed_items=["rifle"], transport_time=transport_time)
        edge = self.graph.edges[0]
        
        self.assertEqual(edge.get_transport_time(), transport_time)
        self.assertTrue(edge.has_transport_time())  # Zero is still a valid time

    def test_negative_transport_time(self):
        """Test edge with negative transport_time (edge case)."""
        transport_time = -1.0
        self.graph.add_edge("n1", "n2", allowed_items=["rifle"], transport_time=transport_time)
        edge = self.graph.edges[0]
        
        self.assertEqual(edge.get_transport_time(), transport_time)
        self.assertTrue(edge.has_transport_time())  # Negative values are allowed (implementation doesn't validate)


if __name__ == "__main__":
    unittest.main()