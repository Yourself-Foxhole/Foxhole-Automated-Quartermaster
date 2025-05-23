"""
Enums used throughout the application.
"""
from enum import Enum, auto

class ItemCategory(Enum):
    """Categories of items in the game."""
    AMMUNITION = auto()
    MEDICAL = auto()
    SUPPLIES = auto()
    WEAPONS = auto()
    VEHICLES = auto()
    STRUCTURES = auto()
    RESOURCES = auto()
    TOOLS = auto()
    UNKNOWN = auto()

class ProductionLocationType(Enum):
    """Types of production and storage locations."""
    FACTORY = auto()
    REFINERY = auto()
    STORAGE_DEPOT = auto()
    BUNKER = auto()
    SAFEHOUSE = auto()
    GARRISON = auto()
    UNKNOWN = auto() 