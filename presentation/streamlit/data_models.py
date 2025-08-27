"""Data models for the Streamlit logistics prototype.

Contains sample Foxhole game data and data structures for the prototype.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import networkx as nx


class ItemType(Enum):
    """Types of items in Foxhole."""

    MATERIAL = "material"
    AMMUNITION = "ammunition"
    MEDICAL = "medical"
    EQUIPMENT = "equipment"
    FUEL = "fuel"
    COMPONENT = "component"


class FacilityType(Enum):
    """Types of facilities in Foxhole."""

    FACTORY = "factory"
    REFINERY = "refinery"
    SEAPORT = "seaport"
    STORAGE_DEPOT = "storage_depot"
    BUNKER_BASE = "bunker_base"
    TOWN_HALL = "town_hall"
    SAFE_HOUSE = "safe_house"
    FIELD_HOSPITAL = "field_hospital"
    VEHICLE_FACTORY = "vehicle_factory"
    SHIPYARD = "shipyard"


@dataclass
class Item:
    """Represents an item in the Foxhole logistics system."""

    name: str
    item_type: ItemType
    description: str = ""

    def __str__(self) -> str:
        return self.name


@dataclass
class InventoryState:
    """Represents the inventory state at a location."""
    item: Item
    quantity: int
    capacity: int = 1000
    
    @property
    def capacity_ratio(self) -> float:
        """Get the capacity utilization ratio (0.0 to 1.0)."""
        return min(self.quantity / self.capacity, 1.0) if self.capacity > 0 else 0.0
    
    @property
    def is_low_stock(self) -> bool:
        """Check if inventory is below 25% capacity."""
        return self.capacity_ratio < 0.25
    
    @property  
    def is_high_stock(self) -> bool:
        """Check if inventory is above 75% capacity."""
        return self.capacity_ratio > 0.75


@dataclass
class Location:
    """Represents a location in the Foxhole world."""
    name: str
    region: str
    facility_type: FacilityType
    position: tuple[float, float] = (0.0, 0.0)  # x, y coordinates
    inventory: Dict[str, InventoryState] = field(default_factory=dict)
    
    def add_inventory(self, item: Item, quantity: int, capacity: int = 1000) -> None:
        """Add inventory for an item at this location."""
        self.inventory[item.name] = InventoryState(item, quantity, capacity)
    
    def get_inventory(self, item_name: str) -> Optional[InventoryState]:
        """Get inventory state for a specific item."""
        return self.inventory.get(item_name)
    
    def get_supply_delta(self, item_name: str, target_quantity: int) -> int:
        """Calculate supply delta (negative = need more, positive = surplus)."""
        current = self.inventory.get(item_name)
        if current is None:
            return -target_quantity
        return current.quantity - target_quantity


# Sample Foxhole game data
FOXHOLE_ITEMS = [
    Item("Basic Materials", ItemType.MATERIAL, "Raw construction materials"),
    Item("Refined Materials", ItemType.MATERIAL, "Processed construction materials"),
    Item("Heavy Explosive Materials", ItemType.MATERIAL, "Materials for explosives"),
    Item("7.62mm Rounds", ItemType.AMMUNITION, "Standard rifle ammunition"),
    Item("12.7mm Rounds", ItemType.AMMUNITION, "Heavy machine gun ammunition"),
    Item("40mm Rounds", ItemType.AMMUNITION, "Artillery ammunition"),
    Item("Rifle Ammo", ItemType.AMMUNITION, "Basic rifle ammunition"),
    Item("SMG Ammo", ItemType.AMMUNITION, "Submachine gun ammunition"),
    Item("LMG Ammo", ItemType.AMMUNITION, "Light machine gun ammunition"),
    Item("Medic Kit", ItemType.MEDICAL, "Basic medical supplies"),
    Item("Trauma Kit", ItemType.MEDICAL, "Advanced medical supplies"),
    Item("Blood Plasma", ItemType.MEDICAL, "Emergency medical supplies"),
    Item("Soldier Supplies", ItemType.EQUIPMENT, "General soldier equipment"),
    Item("Engineer Kit", ItemType.EQUIPMENT, "Engineering tools and supplies"),
    Item("Wrench", ItemType.EQUIPMENT, "Repair tool"),
    Item("Hammer", ItemType.EQUIPMENT, "Construction tool"),
    Item("Shovel", ItemType.EQUIPMENT, "Digging tool"),
    Item("Sandbags", ItemType.EQUIPMENT, "Defensive fortifications"),
    Item("Concrete Materials", ItemType.MATERIAL, "Heavy construction materials"),
    Item("Steel Construction Materials", ItemType.MATERIAL, "Metal construction materials"),
    Item("Shirts", ItemType.EQUIPMENT, "Basic soldier uniforms"),
    Item("Uniforms", ItemType.EQUIPMENT, "Military uniforms"),
    Item("Equipment", ItemType.EQUIPMENT, "General military equipment"),
    Item("Petrol", ItemType.FUEL, "Vehicle fuel"),
    Item("Diesel", ItemType.FUEL, "Heavy vehicle fuel"),
    Item("Heavy Oil", ItemType.FUEL, "Industrial fuel"),
    Item("Components", ItemType.COMPONENT, "Tech components"),
    Item("Tech Parts", ItemType.COMPONENT, "Advanced tech parts"),
    Item("Radio Equipment", ItemType.COMPONENT, "Communication equipment")
]

FOXHOLE_REGIONS = [
    "Abandoned Ward", "Basin Sionnach", "Callahan's Passage", 
    "Deadlands", "Endless Shore", "Farranac Coast",
    "Fisherman's Row", "Great March", "Heartlands",
    "Linn of Mercy", "Marban Hollow", "Reaching Trail",
    "Red River", "Stonecradle", "The Moors",
    "Weathered Expanse", "Westgate", "Origin"
]


def create_sample_locations() -> List[Location]:
    """Create sample locations with realistic Foxhole data."""
    locations = []
    
    # Create locations with different facility types
    location_configs = [
        ("Deadlands Factory", "Deadlands", FacilityType.FACTORY, (100, 200)),
        ("Heartlands Refinery", "Heartlands", FacilityType.REFINERY, (300, 150)),
        ("Fisherman's Row Seaport", "Fisherman's Row", FacilityType.SEAPORT, (50, 400)),
        ("Basin Sionnach Depot", "Basin Sionnach", FacilityType.STORAGE_DEPOT, (250, 300)),
        ("Great March Base", "Great March", FacilityType.BUNKER_BASE, (400, 100)),
        ("Endless Shore Town Hall", "Endless Shore", FacilityType.TOWN_HALL, (200, 250)),
        ("Stonecradle Vehicle Factory", "Stonecradle", FacilityType.VEHICLE_FACTORY, (350, 350)),
        ("Westgate Shipyard", "Westgate", FacilityType.SHIPYARD, (150, 100))
    ]
    
    items_dict = {item.name: item for item in FOXHOLE_ITEMS}
    
    for name, region, facility_type, position in location_configs:
        location = Location(name, region, facility_type, position)
        
        # Add sample inventory based on facility type
        if facility_type == FacilityType.FACTORY:
            location.add_inventory(items_dict["Basic Materials"], 450, 1000)
            location.add_inventory(items_dict["Refined Materials"], 200, 800)
            location.add_inventory(items_dict["Rifle Ammo"], 750, 1000)
            location.add_inventory(items_dict["Shirts"], 300, 500)
        elif facility_type == FacilityType.REFINERY:
            location.add_inventory(items_dict["Basic Materials"], 150, 1000)
            location.add_inventory(items_dict["Refined Materials"], 800, 1000)
            location.add_inventory(items_dict["Petrol"], 600, 1000)
            location.add_inventory(items_dict["Diesel"], 400, 800)
        elif facility_type == FacilityType.SEAPORT:
            location.add_inventory(items_dict["Heavy Explosive Materials"], 100, 500)
            location.add_inventory(items_dict["40mm Rounds"], 250, 600)
            location.add_inventory(items_dict["Components"], 350, 400)
        elif facility_type == FacilityType.STORAGE_DEPOT:
            location.add_inventory(items_dict["Soldier Supplies"], 600, 1000)
            location.add_inventory(items_dict["Medic Kit"], 200, 400)
            location.add_inventory(items_dict["Engineer Kit"], 150, 300)
            location.add_inventory(items_dict["Sandbags"], 800, 1000)
        elif facility_type == FacilityType.BUNKER_BASE:
            location.add_inventory(items_dict["7.62mm Rounds"], 900, 1000)
            location.add_inventory(items_dict["12.7mm Rounds"], 400, 800)
            location.add_inventory(items_dict["Trauma Kit"], 100, 200)
            location.add_inventory(items_dict["Radio Equipment"], 50, 100)
        elif facility_type == FacilityType.VEHICLE_FACTORY:
            location.add_inventory(items_dict["Steel Construction Materials"], 300, 800)
            location.add_inventory(items_dict["Components"], 250, 400)
            location.add_inventory(items_dict["Heavy Oil"], 500, 1000)
        
        locations.append(location)
    
    return locations


def create_logistics_graph(locations: List[Location]) -> nx.DiGraph:
    """Create a directed graph representing logistics connections between locations."""
    G = nx.DiGraph()
    
    # Add nodes for each location
    for location in locations:
        G.add_node(location.name, 
                  location=location,
                  region=location.region,
                  facility_type=location.facility_type.value,
                  position=location.position)
    
    # Add edges representing supply routes (simplified for prototype)
    # In a real system, these would be based on actual road/transport networks
    route_configs = [
        ("Deadlands Factory", "Basin Sionnach Depot", 50),  # distance/cost
        ("Heartlands Refinery", "Deadlands Factory", 75),
        ("Fisherman's Row Seaport", "Basin Sionnach Depot", 60),
        ("Basin Sionnach Depot", "Great March Base", 80),
        ("Endless Shore Town Hall", "Basin Sionnach Depot", 40),
        ("Stonecradle Vehicle Factory", "Great March Base", 65),
        ("Westgate Shipyard", "Fisherman's Row Seaport", 90),
        ("Heartlands Refinery", "Stonecradle Vehicle Factory", 45),
        ("Great March Base", "Deadlands Factory", 70),
        ("Basin Sionnach Depot", "Endless Shore Town Hall", 40)
    ]
    
    for source, target, distance in route_configs:
        if source in G.nodes and target in G.nodes:
            G.add_edge(source, target, distance=distance, transport_cost=distance * 1.5)
    
    return G


# Create instances for the prototype
SAMPLE_LOCATIONS = create_sample_locations()
LOGISTICS_GRAPH = create_logistics_graph(SAMPLE_LOCATIONS)