"""
Priority configuration module for task priority settings.

This module provides:
- Priority multipliers and thresholds
- Location type priority weights
- Item category priority weights
- FTL/FCL capacity settings
"""

from enum import Enum
from typing import Dict, Any, List

class LocationType(Enum):
    """Location types and their base priority weights."""
    BUNKER_BASE = 10  # Frontline bases
    FOB = 8          # Forward operating bases
    SEAPORT = 5      # Regional hubs
    STORAGE_DEPOT = 5 # Regional storage
    FACTORY = 3      # Production facilities
    MPF = 3          # Mass production facilities
    REFINERY = 2     # Resource processing
    MINE = 1         # Resource extraction

class ItemCategory(Enum):
    """Item categories and their base priority weights."""
    CRITICAL = 5     # Essential items (shirts, bmats, etc.)
    COMBAT = 4       # Combat-related items
    SUPPORT = 3      # Support items (meds, etc.)
    LOGISTICS = 2    # Logistics items
    OPTIONAL = 1     # Optional items

class TruckType(Enum):
    """Truck types and their cargo capacities."""
    STANDARD = 15    # Standard truck (15 slots)
    LANDRUNNER = 14  # Dunne Landrunner (14 slots)
    LEATHERBACK = 14 # Dunne Leatherback (14 slots)
    FLATBED = 20     # Flatbed truck (20 slots)

# Priority multipliers
PRIORITY_MULTIPLIERS = {
    "deficit": {
        "critical": 3.0,  # > 90% deficit
        "high": 2.0,      # > 70% deficit
        "medium": 1.5,    # > 50% deficit
        "low": 1.0        # > 30% deficit
    },
    "urgency": 2.0,       # Urgency flag bonus
    "location": 1.5,      # Location importance multiplier
    "time": 1.2          # Time sensitivity multiplier
}

# Priority thresholds
PRIORITY_THRESHOLDS = {
    "deficit": {
        "critical": 0.9,  # 90% deficit
        "high": 0.7,      # 70% deficit
        "medium": 0.5,    # 50% deficit
        "low": 0.3        # 30% deficit
    },
    "time": {
        "critical": 30,   # 30 minutes
        "high": 60,       # 1 hour
        "medium": 120,    # 2 hours
        "low": 240        # 4 hours
    }
}

# FTL/FCL capacity settings
CAPACITY_SETTINGS = {
    "trucks": {
        "standard": 15,    # Standard truck
        "landrunner": 14,  # Dunne Landrunner
        "leatherback": 14, # Dunne Leatherback
        "flatbed": 20      # Flatbed truck
    },
    "fcl": 60,           # Full Container Load capacity
    "train": 13,         # Train capacity
    "ship": 5            # Ship capacity
}

# Priority score ranges
PRIORITY_RANGES = {
    "critical": (8, 10),
    "high": (5, 7),
    "medium": (3, 4),
    "low": (1, 2),
    "optional": (0, 0)
}

def get_location_priority(location_type: str) -> int:
    """Get the base priority for a location type."""
    try:
        return LocationType[location_type.upper()].value
    except KeyError:
        return 1  # Default to lowest priority

def get_item_priority(category: str) -> int:
    """Get the base priority for an item category."""
    try:
        return ItemCategory[category.upper()].value
    except KeyError:
        return 1  # Default to lowest priority

def get_truck_capacity(truck_type: str) -> int:
    """Get the cargo capacity for a truck type."""
    try:
        return CAPACITY_SETTINGS["trucks"][truck_type.lower()]
    except KeyError:
        return CAPACITY_SETTINGS["trucks"]["standard"]  # Default to standard truck

def get_available_truck_types() -> List[str]:
    """Get list of available truck types."""
    return list(CAPACITY_SETTINGS["trucks"].keys())

def get_deficit_multiplier(deficit_percentage: float) -> float:
    """Get the priority multiplier based on deficit percentage."""
    if deficit_percentage >= PRIORITY_THRESHOLDS["deficit"]["critical"]:
        return PRIORITY_MULTIPLIERS["deficit"]["critical"]
    elif deficit_percentage >= PRIORITY_THRESHOLDS["deficit"]["high"]:
        return PRIORITY_MULTIPLIERS["deficit"]["high"]
    elif deficit_percentage >= PRIORITY_THRESHOLDS["deficit"]["medium"]:
        return PRIORITY_MULTIPLIERS["deficit"]["medium"]
    elif deficit_percentage >= PRIORITY_THRESHOLDS["deficit"]["low"]:
        return PRIORITY_MULTIPLIERS["deficit"]["low"]
    return 1.0

def get_time_multiplier(minutes_remaining: int) -> float:
    """Get the priority multiplier based on time sensitivity."""
    if minutes_remaining <= PRIORITY_THRESHOLDS["time"]["critical"]:
        return PRIORITY_MULTIPLIERS["time"]
    elif minutes_remaining <= PRIORITY_THRESHOLDS["time"]["high"]:
        return PRIORITY_MULTIPLIERS["time"] * 0.8
    elif minutes_remaining <= PRIORITY_THRESHOLDS["time"]["medium"]:
        return PRIORITY_MULTIPLIERS["time"] * 0.6
    elif minutes_remaining <= PRIORITY_THRESHOLDS["time"]["low"]:
        return PRIORITY_MULTIPLIERS["time"] * 0.4
    return 1.0

def round_to_capacity(quantity: int, capacity_type: str = "standard") -> int:
    """Round a quantity up to the nearest capacity unit."""
    if capacity_type in CAPACITY_SETTINGS["trucks"]:
        capacity = get_truck_capacity(capacity_type)
    else:
        capacity = CAPACITY_SETTINGS.get(capacity_type, CAPACITY_SETTINGS["trucks"]["standard"])
    return ((quantity + capacity - 1) // capacity) * capacity 