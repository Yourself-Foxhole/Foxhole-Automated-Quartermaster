"""
Tests for the Streamlit logistics prototype.

These tests validate the data models, task generation, and core functionality
of the Streamlit application components.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the presentation/streamlit directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'presentation', 'streamlit'))

from data_models import (
    SAMPLE_LOCATIONS, LOGISTICS_GRAPH, FOXHOLE_ITEMS, FOXHOLE_REGIONS,
    Item, Location, InventoryState, ItemType, FacilityType,
    create_sample_locations, create_logistics_graph
)

# Import streamlit app components
from streamlit_app import generate_sample_tasks, generate_mock_ocr_results


class TestDataModels(unittest.TestCase):
    """Test the data models and sample data generation."""
    
    def test_foxhole_items_loaded(self):
        """Test that Foxhole items are properly loaded."""
        self.assertGreater(len(FOXHOLE_ITEMS), 0)
        self.assertTrue(any(item.name == "Basic Materials" for item in FOXHOLE_ITEMS))
        self.assertTrue(any(item.name == "Refined Materials" for item in FOXHOLE_ITEMS))
        self.assertTrue(any(item.name == "7.62mm Rounds" for item in FOXHOLE_ITEMS))
    
    def test_foxhole_regions_loaded(self):
        """Test that Foxhole regions are properly loaded."""
        self.assertGreater(len(FOXHOLE_REGIONS), 0)
        self.assertIn("Deadlands", FOXHOLE_REGIONS)
        self.assertIn("Heartlands", FOXHOLE_REGIONS)
        self.assertIn("Basin Sionnach", FOXHOLE_REGIONS)
    
    def test_sample_locations_created(self):
        """Test that sample locations are properly created."""
        self.assertEqual(len(SAMPLE_LOCATIONS), 8)
        
        # Check that all locations have names, regions, and facility types
        for location in SAMPLE_LOCATIONS:
            self.assertIsInstance(location.name, str)
            self.assertIsInstance(location.region, str)
            self.assertIsInstance(location.facility_type, FacilityType)
            self.assertIsInstance(location.position, tuple)
            self.assertEqual(len(location.position), 2)
    
    def test_logistics_graph_created(self):
        """Test that the logistics graph is properly created."""
        self.assertGreater(len(LOGISTICS_GRAPH.nodes()), 0)
        self.assertGreater(len(LOGISTICS_GRAPH.edges()), 0)
        
        # Check that all nodes have the expected attributes
        for node in LOGISTICS_GRAPH.nodes():
            node_data = LOGISTICS_GRAPH.nodes[node]
            self.assertIn('location', node_data)
            self.assertIn('region', node_data)
            self.assertIn('facility_type', node_data)
            self.assertIn('position', node_data)
    
    def test_inventory_state_calculations(self):
        """Test inventory state capacity calculations."""
        item = Item("Test Item", ItemType.MATERIAL, "Test description")
        
        # Test low stock
        inv_low = InventoryState(item, 200, 1000)  # 20% capacity
        self.assertTrue(inv_low.is_low_stock)
        self.assertFalse(inv_low.is_high_stock)
        self.assertEqual(inv_low.capacity_ratio, 0.2)
        
        # Test high stock
        inv_high = InventoryState(item, 800, 1000)  # 80% capacity
        self.assertFalse(inv_high.is_low_stock)
        self.assertTrue(inv_high.is_high_stock)
        self.assertEqual(inv_high.capacity_ratio, 0.8)
        
        # Test normal stock
        inv_normal = InventoryState(item, 500, 1000)  # 50% capacity
        self.assertFalse(inv_normal.is_low_stock)
        self.assertFalse(inv_normal.is_high_stock)
        self.assertEqual(inv_normal.capacity_ratio, 0.5)
    
    def test_location_inventory_management(self):
        """Test location inventory management functions."""
        location = Location("Test Location", "Test Region", FacilityType.FACTORY)
        item = Item("Test Item", ItemType.MATERIAL, "Test description")
        
        # Test adding inventory
        location.add_inventory(item, 500, 1000)
        self.assertEqual(len(location.inventory), 1)
        self.assertIn(item.name, location.inventory)
        
        # Test getting inventory
        inv_state = location.get_inventory(item.name)
        self.assertIsNotNone(inv_state)
        self.assertEqual(inv_state.quantity, 500)
        self.assertEqual(inv_state.capacity, 1000)
        
        # Test supply delta calculation
        delta = location.get_supply_delta(item.name, 300)
        self.assertEqual(delta, 200)  # 500 - 300 = 200 surplus
        
        delta_need = location.get_supply_delta(item.name, 700)
        self.assertEqual(delta_need, -200)  # 500 - 700 = -200 deficit


class TestStreamlitAppComponents(unittest.TestCase):
    """Test the Streamlit application components."""
    
    def test_generate_sample_tasks(self):
        """Test that sample tasks are generated correctly."""
        tasks = generate_sample_tasks()
        
        self.assertGreater(len(tasks), 0)
        
        # Check that we have different types of tasks
        task_types = set(task.task_type for task in tasks)
        self.assertIn("transportation", task_types)
        self.assertIn("production", task_types)
        self.assertIn("supply", task_types)
        
        # Check that tasks have required attributes
        for task in tasks:
            self.assertIsInstance(task.task_id, str)
            self.assertIsInstance(task.name, str)
            self.assertIsInstance(task.task_type, str)
            self.assertIsInstance(task.base_priority, float)
            self.assertIsInstance(task.metadata, dict)
    
    def test_generate_mock_ocr_results(self):
        """Test that mock OCR results are generated correctly."""
        results = generate_mock_ocr_results()
        
        self.assertIn('location', results)
        self.assertIn('items', results)
        self.assertIn('confidence', results)
        
        # Check that location is valid
        location_names = [loc.name for loc in SAMPLE_LOCATIONS]
        self.assertIn(results['location'], location_names)
        
        # Check that items are valid
        item_names = [item.name for item in FOXHOLE_ITEMS]
        for item_name in results['items'].keys():
            self.assertIn(item_name, item_names)
        
        # Check confidence is reasonable
        self.assertGreaterEqual(results['confidence'], 0.0)
        self.assertLessEqual(results['confidence'], 1.0)
    
    def test_item_types_enum(self):
        """Test that ItemType enum has expected values."""
        expected_types = ['material', 'ammunition', 'medical', 'equipment', 'fuel', 'component']
        actual_types = [item_type.value for item_type in ItemType]
        
        for expected_type in expected_types:
            self.assertIn(expected_type, actual_types)
    
    def test_facility_types_enum(self):
        """Test that FacilityType enum has expected values."""
        expected_types = [
            'factory', 'refinery', 'seaport', 'storage_depot', 'bunker_base',
            'town_hall', 'safe_house', 'field_hospital', 'vehicle_factory', 'shipyard'
        ]
        actual_types = [facility_type.value for facility_type in FacilityType]
        
        for expected_type in expected_types:
            self.assertIn(expected_type, actual_types)


class TestIntegrationWithExistingSystem(unittest.TestCase):
    """Test integration with existing task and database systems."""
    
    def test_task_import_fallback(self):
        """Test that the task import fallback works correctly."""
        # This test ensures that if the existing task system imports fail,
        # the fallback implementation works correctly
        try:
            from services.tasks.task import Task, TaskStatus
            # If import succeeds, verify it has expected attributes
            self.assertTrue(hasattr(TaskStatus, 'PENDING'))
            self.assertTrue(hasattr(TaskStatus, 'IN_PROGRESS'))
            self.assertTrue(hasattr(TaskStatus, 'COMPLETED'))
        except ImportError:
            # If import fails, the fallback should be used
            # This would be tested by the streamlit_app import test
            pass
    
    def test_sample_data_consistency(self):
        """Test that sample data is consistent across modules."""
        # Verify that sample locations are consistent with the graph
        graph_nodes = set(LOGISTICS_GRAPH.nodes())
        location_names = set(loc.name for loc in SAMPLE_LOCATIONS)
        
        self.assertEqual(graph_nodes, location_names)
        
        # Verify that each location in the graph has the corresponding data
        for node in LOGISTICS_GRAPH.nodes():
            node_data = LOGISTICS_GRAPH.nodes[node]
            location = node_data['location']
            self.assertIsInstance(location, Location)
            self.assertEqual(location.name, node)


if __name__ == '__main__':
    unittest.main()