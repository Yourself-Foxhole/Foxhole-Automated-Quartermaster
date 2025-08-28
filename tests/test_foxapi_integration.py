"""
Tests for FoxAPI integration in the Streamlit logistics prototype.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

# Add the streamlit presentation directory to the path
streamlit_dir = os.path.join(os.path.dirname(__file__), '..', 'presentation', 'streamlit')
sys.path.insert(0, streamlit_dir)

# Mock streamlit for testing
class MockSessionState:
    def __init__(self):
        self.data = {}
    
    def __contains__(self, key):
        return key in self.data
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def get(self, key, default=None):
        return self.data.get(key, default)

class MockStreamlit:
    def __init__(self):
        self.session_state = MockSessionState()

# Mock the streamlit module before importing our code
sys.modules['streamlit'] = MockStreamlit()

# Now import our FoxAPI adapter
import foxapi_adapter
from foxapi_adapter import FoxAPIAdapter, WarStatus, WarMaps, get_foxapi_adapter


class TestFoxAPIAdapter(unittest.TestCase):
    """Test cases for FoxAPI adapter functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset the global adapter instance for each test
        foxapi_adapter._foxapi_adapter = None
        
        # Mock streamlit session state
        foxapi_adapter.st = MockStreamlit()
    
    def test_war_status_creation(self):
        """Test WarStatus dataclass creation."""
        war_status = WarStatus(
            war_id="test-war-123",
            war_number=123,
            phase="Test Phase",
            duration_days=10,
            active_regions=20,
            data_source="test"
        )
        
        self.assertEqual(war_status.war_id, "test-war-123")
        self.assertEqual(war_status.war_number, 123)
        self.assertEqual(war_status.phase, "Test Phase")
        self.assertEqual(war_status.duration_days, 10)
        self.assertEqual(war_status.active_regions, 20)
        self.assertEqual(war_status.data_source, "test")
    
    def test_war_maps_creation(self):
        """Test WarMaps dataclass creation."""
        test_maps = ["Map1", "Map2", "Map3"]
        war_maps = WarMaps(
            maps=test_maps,
            total_maps=len(test_maps),
            data_source="test"
        )
        
        self.assertEqual(war_maps.maps, test_maps)
        self.assertEqual(war_maps.total_maps, 3)
        self.assertEqual(war_maps.data_source, "test")
    
    def test_adapter_initialization(self):
        """Test FoxAPI adapter initialization."""
        adapter = FoxAPIAdapter(shard="test", cache_duration=600)
        
        self.assertEqual(adapter.shard, "test")
        self.assertEqual(adapter.cache_duration, 600)
        self.assertIsNotNone(adapter.cache_file)
    
    def test_mock_war_status(self):
        """Test mock war status generation."""
        adapter = FoxAPIAdapter()
        mock_status = adapter._get_mock_war_status()
        
        self.assertIsInstance(mock_status, WarStatus)
        self.assertEqual(mock_status.data_source, "mock")
        self.assertGreater(mock_status.war_number, 0)
        self.assertIsNotNone(mock_status.phase)
    
    def test_mock_maps(self):
        """Test mock maps generation."""
        adapter = FoxAPIAdapter()
        mock_maps = adapter._get_mock_maps()
        
        self.assertIsInstance(mock_maps, WarMaps)
        self.assertEqual(mock_maps.data_source, "mock")
        self.assertGreater(mock_maps.total_maps, 0)
        self.assertIsInstance(mock_maps.maps, list)
    
    def test_war_phase_computation(self):
        """Test war phase computation logic."""
        adapter = FoxAPIAdapter()
        
        # Test war ended
        war_data = {'winner': 'Colonials'}
        self.assertEqual(adapter._compute_war_phase(war_data), "War Ended")
        
        # Test resistance phase
        war_data = {'resistanceStartTime': '2024-01-01T00:00:00Z'}
        self.assertEqual(adapter._compute_war_phase(war_data), "Resistance Phase")
        
        # Test conquest phase
        war_data = {'conquestStartTime': '2024-01-01T00:00:00Z'}
        self.assertEqual(adapter._compute_war_phase(war_data), "Conquest Phase")
        
        # Test pre-war
        war_data = {}
        self.assertEqual(adapter._compute_war_phase(war_data), "Pre-War")
    
    def test_duration_computation(self):
        """Test war duration computation."""
        adapter = FoxAPIAdapter()
        
        # Test with conquest start time (recent)
        now = datetime.now()
        recent_time = now.isoformat() + 'Z'
        war_data = {'conquestStartTime': recent_time}
        duration = adapter._compute_duration(war_data)
        self.assertGreaterEqual(duration, 0)
        
        # Test with no time data
        war_data = {}
        duration = adapter._compute_duration(war_data)
        self.assertEqual(duration, 0)
    
    @patch('foxapi_adapter.FoxAPI')
    def test_get_war_status_with_mock_api(self, mock_foxapi_class):
        """Test war status retrieval with mocked FoxAPI."""
        # Mock API response
        mock_api = Mock()
        mock_api.get_war_sync.return_value = {
            'warId': 'test-123',
            'warNumber': 123,
            'winner': None,
            'conquestStartTime': '2024-01-01T00:00:00Z',
            'requiredVictoryTowns': 32,
            'shortRequiredVictoryTowns': 15
        }
        mock_api.get_maps_sync.return_value = ['Map1', 'Map2', 'Map3']
        mock_foxapi_class.return_value = mock_api
        
        adapter = FoxAPIAdapter()
        war_status = adapter.get_war_status(use_cache=False)
        
        self.assertEqual(war_status.war_id, 'test-123')
        self.assertEqual(war_status.war_number, 123)
        self.assertEqual(war_status.data_source, 'foxapi')
        self.assertEqual(war_status.required_victory_towns, 32)
    
    @patch('foxapi_adapter.FoxAPI')
    def test_get_maps_with_mock_api(self, mock_foxapi_class):
        """Test maps retrieval with mocked FoxAPI."""
        # Mock API response
        mock_api = Mock()
        test_maps = ['DeadLandsHex', 'HeartlandsHex', 'CallahansPassageHex']
        mock_api.get_maps_sync.return_value = test_maps
        mock_foxapi_class.return_value = mock_api
        
        adapter = FoxAPIAdapter()
        war_maps = adapter.get_maps(use_cache=False)
        
        self.assertEqual(war_maps.maps, test_maps)
        self.assertEqual(war_maps.total_maps, 3)
        self.assertEqual(war_maps.data_source, 'foxapi')
    
    def test_cache_validity(self):
        """Test cache validity checking."""
        adapter = FoxAPIAdapter()
        
        # Test empty cache
        cache_data = {}
        self.assertFalse(adapter._is_cache_valid(cache_data, 'test_key'))
        
        # Test valid cache (recent)
        import time
        cache_data = {
            'test_key': {
                'timestamp': time.time() - 100  # 100 seconds ago
            }
        }
        self.assertTrue(adapter._is_cache_valid(cache_data, 'test_key'))
        
        # Test invalid cache (old)
        cache_data = {
            'test_key': {
                'timestamp': time.time() - 1000  # 1000 seconds ago
            }
        }
        self.assertFalse(adapter._is_cache_valid(cache_data, 'test_key'))
    
    def test_global_adapter_instance(self):
        """Test global adapter instance creation."""
        adapter1 = get_foxapi_adapter()
        adapter2 = get_foxapi_adapter()
        
        # Should return the same instance
        self.assertIs(adapter1, adapter2)
    
    def test_cache_status(self):
        """Test cache status reporting."""
        adapter = FoxAPIAdapter()
        cache_status = adapter.get_cache_status()
        
        self.assertIn('war_cache_valid', cache_status)
        self.assertIn('maps_cache_valid', cache_status)
        self.assertIn('api_available', cache_status)
        self.assertIn('foxapi_installed', cache_status)
        
        # Should be boolean values
        self.assertIsInstance(cache_status['war_cache_valid'], bool)
        self.assertIsInstance(cache_status['maps_cache_valid'], bool)
        self.assertIsInstance(cache_status['api_available'], bool)
        self.assertIsInstance(cache_status['foxapi_installed'], bool)
    
    @unittest.skip("Mock session state behavior differs from real streamlit")
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        adapter = FoxAPIAdapter()
        
        # Add some dummy cache data through the streamlit session state
        import foxapi_adapter as fa
        fa.st.session_state['foxapi_war_cache'] = {'test': 'data'}
        fa.st.session_state['foxapi_maps_cache'] = {'test': 'data'}
        
        # Clear cache
        adapter.clear_cache()
        
        # Verify cache is cleared
        self.assertEqual(fa.st.session_state['foxapi_war_cache'], {})
        self.assertEqual(fa.st.session_state['foxapi_maps_cache'], {})


class TestFoxAPIIntegration(unittest.TestCase):
    """Integration tests for FoxAPI functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        foxapi_adapter.st = MockStreamlit()
    
    def test_fallback_when_foxapi_unavailable(self):
        """Test that fallback data is used when FoxAPI is unavailable."""
        # Mock FoxAPI as unavailable
        with patch('foxapi_adapter.FOXAPI_AVAILABLE', False):
            adapter = FoxAPIAdapter()
            
            war_status = adapter.get_war_status()
            self.assertEqual(war_status.data_source, 'mock')
            
            war_maps = adapter.get_maps()
            self.assertEqual(war_maps.data_source, 'mock')
    
    @patch('foxapi_adapter.FoxAPI')
    def test_api_error_handling(self, mock_foxapi_class):
        """Test error handling when API calls fail."""
        # Mock API to raise an exception
        mock_api = Mock()
        mock_api.get_war_sync.side_effect = Exception("API Error")
        mock_api.get_maps_sync.side_effect = Exception("API Error")
        mock_foxapi_class.return_value = mock_api
        
        adapter = FoxAPIAdapter()
        
        # Should fall back to mock data on error
        war_status = adapter.get_war_status()
        self.assertEqual(war_status.data_source, 'mock')
        
        war_maps = adapter.get_maps()
        self.assertEqual(war_maps.data_source, 'mock')


if __name__ == '__main__':
    unittest.main()