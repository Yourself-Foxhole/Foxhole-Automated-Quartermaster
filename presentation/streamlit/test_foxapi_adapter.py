#!/usr/bin/env python3
"""
Simple test script for FoxAPI adapter functionality.
"""

import sys
import os

# Add the parent directory to the path to import the adapter
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock streamlit session state for testing
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

# Mock streamlit module
class MockStreamlit:
    def __init__(self):
        self.session_state = MockSessionState()

# Inject mock streamlit
import foxapi_adapter
foxapi_adapter.st = MockStreamlit()

def test_foxapi_adapter():
    """Test the FoxAPI adapter functionality."""
    print("Testing FoxAPI adapter...")
    
    # Test basic initialization
    adapter = foxapi_adapter.get_foxapi_adapter()
    print(f"✓ Adapter initialized")
    
    # Test war status retrieval
    war_status = adapter.get_war_status()
    print(f"✓ War Status retrieved:")
    print(f"  - War Number: {war_status.war_number}")
    print(f"  - Phase: {war_status.phase}")
    print(f"  - Duration: {war_status.duration_days} days")
    print(f"  - Active Regions: {war_status.active_regions}")
    print(f"  - Data Source: {war_status.data_source}")
    
    # Test maps retrieval
    maps = adapter.get_maps()
    print(f"✓ Maps retrieved:")
    print(f"  - Total Maps: {maps.total_maps}")
    print(f"  - Data Source: {maps.data_source}")
    print(f"  - Sample Maps: {maps.maps[:3] if maps.maps else 'None'}")
    
    # Test cache status
    cache_status = adapter.get_cache_status()
    print(f"✓ Cache Status:")
    print(f"  - API Available: {cache_status['api_available']}")
    print(f"  - FoxAPI Installed: {cache_status['foxapi_installed']}")
    print(f"  - War Cache Valid: {cache_status['war_cache_valid']}")
    print(f"  - Maps Cache Valid: {cache_status['maps_cache_valid']}")
    
    print("\n🎉 All tests passed!")

if __name__ == "__main__":
    test_foxapi_adapter()