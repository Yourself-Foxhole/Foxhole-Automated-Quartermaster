"""
FoxAPI adapter for Foxhole War Status integration.

This module provides a clean interface to the FoxAPI library with error handling,
caching, and fallback mechanisms for the Streamlit logistics prototype.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import streamlit as st

try:
    from foxapi import FoxAPI
    FOXAPI_AVAILABLE = True
except ImportError:
    FOXAPI_AVAILABLE = False


@dataclass
class WarStatus:
    """War status data structure."""
    war_id: str = ""
    war_number: int = 0
    winner: Optional[str] = None
    conquest_start_time: Optional[str] = None
    conquest_end_time: Optional[str] = None
    resistance_start_time: Optional[str] = None
    scheduled_conquest_end_time: Optional[str] = None
    required_victory_towns: int = 0
    short_required_victory_towns: int = 0
    
    # Computed fields
    phase: str = "Unknown"
    duration_days: int = 0
    active_regions: int = 0
    
    # Metadata
    last_updated: str = ""
    data_source: str = "mock"


@dataclass
class WarMaps:
    """War maps data structure."""
    maps: List[str] = None
    total_maps: int = 0
    last_updated: str = ""
    data_source: str = "mock"
    
    def __post_init__(self):
        if self.maps is None:
            self.maps = []


class FoxAPIAdapter:
    """
    Adapter for FoxAPI with caching and error handling.
    
    Provides a clean interface to fetch war status and map data from the Foxhole API
    with automatic fallback to cached or mock data when the API is unavailable.
    """
    
    def __init__(self, shard: str = "1", cache_duration: int = 300):
        """
        Initialize the FoxAPI adapter.
        
        Args:
            shard: Foxhole shard to connect to (default: "1")
            cache_duration: Cache duration in seconds (default: 300 = 5 minutes)
        """
        self.shard = shard
        self.cache_duration = cache_duration
        self.cache_file = "foxapi_cache.json"
        self.api = None
        
        if FOXAPI_AVAILABLE:
            try:
                self.api = FoxAPI(shard=shard, safe_mode=True)
            except Exception as e:
                print("Warning: Failed to initialize FoxAPI:", str(e))
                self.api = None
        
        # Initialize session state for caching
        if 'foxapi_war_cache' not in st.session_state:
            st.session_state.foxapi_war_cache = {}
        if 'foxapi_maps_cache' not in st.session_state:
            st.session_state.foxapi_maps_cache = {}
    
    def _is_cache_valid(self, cache_data: Dict, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if not cache_data or cache_key not in cache_data:
            return False
        
        last_update = cache_data[cache_key].get('timestamp', 0)
        return time.time() - last_update < self.cache_duration
    
    def _get_mock_war_status(self) -> WarStatus:
        """Get mock war status data as fallback."""
        return WarStatus(
            war_id="mock-105",
            war_number=105,
            winner=None,
            conquest_start_time="2024-01-01T00:00:00Z",
            resistance_start_time="2024-01-24T00:00:00Z",
            required_victory_towns=32,
            short_required_victory_towns=15,
            phase="Resistance Phase",
            duration_days=23,
            active_regions=18,
            last_updated=datetime.now().isoformat(),
            data_source="mock"
        )
    
    def _get_mock_maps(self) -> WarMaps:
        """Get mock maps data as fallback."""
        mock_maps = [
            "DeadLandsHex", "CallahansPassageHex", "MarbanHollow", "UmbralWildwoodHex",
            "HeartlandsHex", "LochMorHex", "LinnMercyHex", "ReachingTrailHex",
            "StonecradleHex", "FarranacCoastHex", "WestgateHex", "AshFieldsHex",
            "MooringCountyHex", "WeatheredExpanseHex", "DrownedValeHex", "ShackledChasmHex",
            "EndlessShoreHex", "AllodsBightHex", "NevishLineHex", "AcrithiaHex"
        ]
        
        return WarMaps(
            maps=mock_maps,
            total_maps=len(mock_maps),
            last_updated=datetime.now().isoformat(),
            data_source="mock"
        )
    
    def _compute_war_phase(self, war_data: Dict) -> str:
        """Compute current war phase from war data."""
        if war_data.get('winner'):
            return "War Ended"
        elif war_data.get('resistanceStartTime'):
            return "Resistance Phase"
        elif war_data.get('conquestStartTime'):
            return "Conquest Phase"
        else:
            return "Pre-War"
    
    def _compute_duration(self, war_data: Dict) -> int:
        """Compute war duration in days."""
        try:
            start_time = war_data.get('conquestStartTime') or war_data.get('resistanceStartTime')
            if start_time:
                start_date = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                duration = datetime.now(start_date.tzinfo) - start_date
                return max(1, duration.days)
        except Exception:
            pass
        return 0
    
    def get_war_status(self, use_cache: bool = True) -> WarStatus:
        """
        Get current war status with caching and error handling.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            WarStatus object with current war information
        """
        # Check cache first
        if use_cache and self._is_cache_valid(st.session_state.foxapi_war_cache, 'war_status'):
            cached_data = st.session_state.foxapi_war_cache['war_status']['data']
            return WarStatus(**cached_data)
        
        # Try to fetch from API
        if self.api:
            try:
                war_data = self.api.get_war_sync(use_cache=use_cache)
                if war_data:
                    # Get maps for active region count
                    maps_data = self.get_maps(use_cache=use_cache)
                    
                    war_status = WarStatus(
                        war_id=war_data.get('warId', ''),
                        war_number=war_data.get('warNumber', 0),
                        winner=war_data.get('winner'),
                        conquest_start_time=war_data.get('conquestStartTime'),
                        conquest_end_time=war_data.get('conquestEndTime'),
                        resistance_start_time=war_data.get('resistanceStartTime'),
                        scheduled_conquest_end_time=war_data.get('scheduledConquestEndTime'),
                        required_victory_towns=war_data.get('requiredVictoryTowns', 0),
                        short_required_victory_towns=war_data.get('shortRequiredVictoryTowns', 0),
                        phase=self._compute_war_phase(war_data),
                        duration_days=self._compute_duration(war_data),
                        active_regions=maps_data.total_maps,
                        last_updated=datetime.now().isoformat(),
                        data_source="foxapi"
                    )
                    
                    # Cache the result
                    st.session_state.foxapi_war_cache['war_status'] = {
                        'data': asdict(war_status),
                        'timestamp': time.time()
                    }
                    
                    return war_status
                    
            except Exception as e:
                print(f"Warning: Failed to fetch war data from FoxAPI: {e}")
        
        # Fallback to mock data
        return self._get_mock_war_status()
    
    def get_maps(self, use_cache: bool = True) -> WarMaps:
        """
        Get available maps with caching and error handling.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            WarMaps object with available maps information
        """
        # Check cache first
        if use_cache and self._is_cache_valid(st.session_state.foxapi_maps_cache, 'maps'):
            cached_data = st.session_state.foxapi_maps_cache['maps']['data']
            return WarMaps(**cached_data)
        
        # Try to fetch from API
        if self.api:
            try:
                maps_data = self.api.get_maps_sync(use_cache=use_cache)
                if maps_data:
                    war_maps = WarMaps(
                        maps=maps_data,
                        total_maps=len(maps_data),
                        last_updated=datetime.now().isoformat(),
                        data_source="foxapi"
                    )
                    
                    # Cache the result
                    st.session_state.foxapi_maps_cache['maps'] = {
                        'data': asdict(war_maps),
                        'timestamp': time.time()
                    }
                    
                    return war_maps
                    
            except Exception as e:
                print(f"Warning: Failed to fetch maps data from FoxAPI: {e}")
        
        # Fallback to mock data
        return self._get_mock_maps()
    
    def get_hexagon_summary(self, hexagon: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Get summary information for a specific hexagon.
        
        Args:
            hexagon: Hexagon name to get data for
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary with hexagon summary or None if unavailable
        """
        if not self.api:
            return None
            
        try:
            # Get basic hexagon data (war report for casualties, dynamic for current state)
            war_report = self.api.get_war_report_sync(hexagon, use_cache=use_cache)
            dynamic_data = self.api.get_dynamic_sync(hexagon, use_cache=use_cache)
            
            if war_report and dynamic_data:
                return {
                    'hexagon': hexagon,
                    'total_enlistments': war_report.get('totalEnlistments', 0),
                    'colonial_casualties': war_report.get('colonialCasualties', 0),
                    'warden_casualties': war_report.get('wardenCasualties', 0),
                    'day_of_war': war_report.get('dayOfWar', 0),
                    'map_items_count': len(dynamic_data.get('mapItems', [])),
                    'last_updated': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"Warning: Failed to fetch hexagon data for {hexagon}: {e}")
            
        return None
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        st.session_state.foxapi_war_cache = {}
        st.session_state.foxapi_maps_cache = {}
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status information."""
        status = {
            'war_cache_valid': self._is_cache_valid(st.session_state.foxapi_war_cache, 'war_status'),
            'maps_cache_valid': self._is_cache_valid(st.session_state.foxapi_maps_cache, 'maps'),
            'api_available': self.api is not None,
            'foxapi_installed': FOXAPI_AVAILABLE
        }
        
        if st.session_state.foxapi_war_cache.get('war_status'):
            status['war_cache_age'] = int(time.time() - st.session_state.foxapi_war_cache['war_status']['timestamp'])
        
        if st.session_state.foxapi_maps_cache.get('maps'):
            status['maps_cache_age'] = int(time.time() - st.session_state.foxapi_maps_cache['maps']['timestamp'])
            
        return status


# Global adapter instance
_foxapi_adapter = None


def get_foxapi_adapter(shard: str = "1") -> FoxAPIAdapter:
    """Get or create the global FoxAPI adapter instance."""
    global _foxapi_adapter
    if _foxapi_adapter is None:
        _foxapi_adapter = FoxAPIAdapter(shard=shard)
    return _foxapi_adapter