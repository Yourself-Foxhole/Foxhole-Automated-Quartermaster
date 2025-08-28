"""Tests for Google Sheets integration.

This module contains unit and integration tests for the Google Sheets backend,
configuration management, and UI components.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime
import tempfile
import os

# Import modules to test
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'presentation', 'streamlit'))

from gsheets_backend import GSheetsDataBackend
from gsheets_config import GSheetsConfig
from data_models import Location, Item, InventoryState, ItemType, FacilityType


class TestGSheetsConfig(unittest.TestCase):
    """Test Google Sheets configuration management."""
    
    def setUp(self):
        """Set up test configuration."""
        self.config = GSheetsConfig()
        # Clear cache
        self.config._config_cache = None
    
    def test_config_validation_missing_config(self):
        """Test validation with missing configuration."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('streamlit.secrets', {}, create=True):
                is_valid, error = self.config.validate_config()
                self.assertFalse(is_valid)
                self.assertIn("missing or incomplete", error)
    
    def test_config_validation_missing_fields(self):
        """Test validation with missing required fields."""
        config_data = {
            'spreadsheet': 'test-sheet',
            'type': 'service_account',
            'project_id': 'test-project'
            # Missing private_key and client_email
        }
        
        self.config._config_cache = config_data
        is_valid, error = self.config.validate_config()
        self.assertFalse(is_valid)
        self.assertIn("Missing service account fields", error)
    
    def test_config_validation_complete(self):
        """Test validation with complete configuration."""
        config_data = {
            'spreadsheet': 'test-sheet',
            'type': 'service_account',
            'project_id': 'test-project',
            'private_key': 'test-key',
            'client_email': 'test@example.com',
            'client_id': 'test-client-id'
        }
        
        self.config._config_cache = config_data
        is_valid, error = self.config.validate_config()
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_worksheet_name_mapping(self):
        """Test worksheet name mapping."""
        config_data = {
            'inventory_worksheet': 'CustomInventory',
            'tasks_worksheet': 'CustomTasks'
        }
        
        self.config._config_cache = config_data
        
        self.assertEqual(self.config.get_worksheet_name('inventory'), 'CustomInventory')
        self.assertEqual(self.config.get_worksheet_name('tasks'), 'CustomTasks')
        self.assertEqual(self.config.get_worksheet_name('unknown'), 'Unknown')
    
    def test_secrets_template_generation(self):
        """Test secrets template generation."""
        template = self.config.create_streamlit_secrets_template()
        
        self.assertIn('[connections.gsheets]', template)
        self.assertIn('spreadsheet =', template)
        self.assertIn('type = "service_account"', template)
        self.assertIn('private_key =', template)


class TestGSheetsDataBackend(unittest.TestCase):
    """Test Google Sheets data backend."""
    
    def setUp(self):
        """Set up test backend."""
        self.backend = GSheetsDataBackend()
        
        # Mock streamlit connection
        self.mock_connection = Mock()
        self.backend._connection = self.mock_connection
        self.backend._connection_status = "connected"
    
    def test_locations_to_dataframes(self):
        """Test conversion of Location objects to DataFrames."""
        # Create test data
        item = Item("Test Item", ItemType.MATERIAL)
        location = Location("Test Location", "Test Region", FacilityType.FACTORY)
        location.add_inventory(item, 100, 500)
        
        inventory_df, locations_df = self.backend._locations_to_dataframes([location])
        
        # Check locations DataFrame
        self.assertEqual(len(locations_df), 1)
        self.assertEqual(locations_df.iloc[0]['name'], "Test Location")
        self.assertEqual(locations_df.iloc[0]['region'], "Test Region")
        self.assertEqual(locations_df.iloc[0]['facility_type'], "factory")
        
        # Check inventory DataFrame
        self.assertEqual(len(inventory_df), 1)
        self.assertEqual(inventory_df.iloc[0]['location_name'], "Test Location")
        self.assertEqual(inventory_df.iloc[0]['item_name'], "Test Item")
        self.assertEqual(inventory_df.iloc[0]['item_type'], "material")
        self.assertEqual(inventory_df.iloc[0]['quantity'], 100)
        self.assertEqual(inventory_df.iloc[0]['capacity'], 500)
    
    def test_dataframes_to_locations(self):
        """Test conversion of DataFrames back to Location objects."""
        # Create test DataFrames
        locations_df = pd.DataFrame([{
            'name': 'Test Location',
            'region': 'Test Region',
            'facility_type': 'factory',
            'position_x': 100.0,
            'position_y': 200.0
        }])
        
        inventory_df = pd.DataFrame([{
            'location_name': 'Test Location',
            'item_name': 'Test Item',
            'item_type': 'material',
            'quantity': 100,
            'capacity': 500,
            'last_updated': datetime.now().isoformat()
        }])
        
        locations = self.backend._dataframes_to_locations(inventory_df, locations_df)
        
        self.assertEqual(len(locations), 1)
        location = locations[0]
        self.assertEqual(location.name, "Test Location")
        self.assertEqual(location.region, "Test Region")
        self.assertEqual(location.facility_type, FacilityType.FACTORY)
        self.assertEqual(location.position, (100.0, 200.0))
        
        # Check inventory
        self.assertIn("Test Item", location.inventory)
        inventory_state = location.inventory["Test Item"]
        self.assertEqual(inventory_state.quantity, 100)
        self.assertEqual(inventory_state.capacity, 500)
    
    @patch('streamlit.connection')
    def test_connection_initialization(self, mock_st_connection):
        """Test connection initialization."""
        backend = GSheetsDataBackend()
        mock_connection = Mock()
        mock_st_connection.return_value = mock_connection
        
        # Test successful connection
        connection = backend.connection
        self.assertEqual(connection, mock_connection)
        self.assertEqual(backend.connection_status, "connected")
        
        # Test connection error
        mock_st_connection.side_effect = Exception("Connection failed")
        backend._connection = None
        connection = backend.connection
        self.assertIsNone(connection)
        self.assertEqual(backend.connection_status, "error")
        self.assertIn("Connection failed", backend.last_error)
    
    def test_save_inventory_data(self):
        """Test saving inventory data to Google Sheets."""
        # Create test data
        item = Item("Test Item", ItemType.MATERIAL)
        location = Location("Test Location", "Test Region", FacilityType.FACTORY)
        location.add_inventory(item, 100, 500)
        
        # Mock successful update
        self.mock_connection.update.return_value = True
        
        result = self.backend.save_inventory_data([location])
        
        self.assertTrue(result)
        self.assertEqual(self.mock_connection.update.call_count, 2)  # Two sheets updated
    
    def test_load_inventory_data_empty_sheets(self):
        """Test loading inventory data when sheets are empty."""
        # Mock empty DataFrames
        self.mock_connection.read.return_value = pd.DataFrame()
        
        # Mock save_inventory_data to return True
        with patch.object(self.backend, 'save_inventory_data', return_value=True):
            locations = self.backend.load_inventory_data()
        
        # Should return sample data and populate sheets
        self.assertTrue(len(locations) > 0)
    
    def test_analytics_logging(self):
        """Test analytics metric logging."""
        # Mock existing analytics data
        existing_data = pd.DataFrame([{
            'metric_name': 'test_metric',
            'metric_value': 1,
            'timestamp': datetime.now().isoformat(),
            'metadata': ''
        }])
        
        self.mock_connection.read.return_value = existing_data
        self.mock_connection.update.return_value = True
        
        result = self.backend.log_analytics_metric("new_metric", 5, {"test": "data"})
        
        self.assertTrue(result)
        self.mock_connection.update.assert_called_once()
    
    def test_connection_test(self):
        """Test connection testing functionality."""
        # Test successful connection
        self.mock_connection.read.return_value = pd.DataFrame()
        result = self.backend.test_connection()
        self.assertTrue(result)
        
        # Test failed connection
        self.mock_connection.read.side_effect = Exception("Connection test failed")
        result = self.backend.test_connection()
        self.assertFalse(result)
    
    def test_worksheet_initialization(self):
        """Test worksheet initialization."""
        # Mock worksheet that doesn't exist
        self.mock_connection.read.side_effect = Exception("Worksheet not found")
        self.mock_connection.create.return_value = True
        
        result = self.backend.initialize_sheets()
        
        self.assertTrue(result)
        # Should try to create 4 worksheets
        self.assertEqual(self.mock_connection.create.call_count, 4)


class TestGSheetsIntegration(unittest.TestCase):
    """Integration tests for Google Sheets functionality."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.backend = GSheetsDataBackend()
        self.config = GSheetsConfig()
    
    def test_end_to_end_data_flow(self):
        """Test complete data flow from objects to sheets and back."""
        # Create test location with inventory
        item = Item("Integration Test Item", ItemType.AMMUNITION)
        location = Location("Integration Test Location", "Test Region", FacilityType.BUNKER_BASE)
        location.add_inventory(item, 250, 1000)
        locations = [location]
        
        # Mock connection
        mock_connection = Mock()
        self.backend._connection = mock_connection
        self.backend._connection_status = "connected"
        
        # Test save
        mock_connection.update.return_value = True
        save_result = self.backend.save_inventory_data(locations)
        self.assertTrue(save_result)
        
        # Test load - mock the DataFrames that would be returned
        locations_df = pd.DataFrame([{
            'name': 'Integration Test Location',
            'region': 'Test Region',
            'facility_type': 'bunker_base',
            'position_x': 0.0,
            'position_y': 0.0
        }])
        
        inventory_df = pd.DataFrame([{
            'location_name': 'Integration Test Location',
            'item_name': 'Integration Test Item',
            'item_type': 'ammunition',
            'quantity': 250,
            'capacity': 1000,
            'last_updated': datetime.now().isoformat()
        }])
        
        mock_connection.read.side_effect = [inventory_df, locations_df]
        
        loaded_locations = self.backend.load_inventory_data()
        
        # Verify loaded data matches original
        self.assertEqual(len(loaded_locations), 1)
        loaded_location = loaded_locations[0]
        self.assertEqual(loaded_location.name, "Integration Test Location")
        self.assertEqual(loaded_location.region, "Test Region")
        self.assertEqual(loaded_location.facility_type, FacilityType.BUNKER_BASE)
        
        # Check inventory
        self.assertIn("Integration Test Item", loaded_location.inventory)
        inventory_state = loaded_location.inventory["Integration Test Item"]
        self.assertEqual(inventory_state.quantity, 250)
        self.assertEqual(inventory_state.capacity, 1000)
        self.assertEqual(inventory_state.item.item_type, ItemType.AMMUNITION)


class TestErrorHandling(unittest.TestCase):
    """Test error handling in Google Sheets integration."""
    
    def setUp(self):
        """Set up error handling tests."""
        self.backend = GSheetsDataBackend()
    
    def test_connection_error_handling(self):
        """Test handling of connection errors."""
        # Mock connection that raises exception
        with patch('streamlit.connection') as mock_st_connection:
            mock_st_connection.side_effect = Exception("API quota exceeded")
            
            backend = GSheetsDataBackend()
            connection = backend.connection
            
            self.assertIsNone(connection)
            self.assertEqual(backend.connection_status, "error")
            self.assertIn("API quota exceeded", backend.last_error)
    
    def test_data_operation_error_handling(self):
        """Test handling of data operation errors."""
        # Mock connection that fails during operations
        mock_connection = Mock()
        mock_connection.read.side_effect = Exception("Network error")
        mock_connection.update.side_effect = Exception("Write permission denied")
        
        self.backend._connection = mock_connection
        self.backend._connection_status = "connected"
        
        # Test failed load
        locations = self.backend.load_inventory_data()
        # Should return sample data as fallback
        self.assertTrue(len(locations) > 0)
        
        # Test failed save
        result = self.backend.save_inventory_data(locations)
        self.assertFalse(result)
        self.assertIn("Write permission denied", self.backend.last_error)
    
    def test_analytics_error_handling(self):
        """Test handling of analytics errors."""
        mock_connection = Mock()
        mock_connection.read.side_effect = Exception("Analytics sheet not found")
        
        self.backend._connection = mock_connection
        self.backend._connection_status = "connected"
        
        # Test failed analytics logging
        result = self.backend.log_analytics_metric("test_metric", 1)
        self.assertFalse(result)
        
        # Test failed analytics retrieval
        df = self.backend.get_analytics_metrics()
        self.assertTrue(df.empty)


if __name__ == '__main__':
    unittest.main()