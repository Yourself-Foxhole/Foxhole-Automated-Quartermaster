"""
Transportation Cost Algorithm for Foxhole Logistics Network

This module implements transportation cost calculations and decision-making
logic to determine whether to transport items or produce them locally.
Features are optional and default to production-only logic when not configured.

Based on requirements in docs/transportation-cost.md
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
import time


class VehicleType(Enum):
    """Standard vehicle types for Foxhole logistics"""
    FLATBED_TRAIN = "flatbed_train"
    FREIGHTER = "freighter"  
    FLATBED = "flatbed"
    BASE_TRUCK = "base_truck"
    SPECIALIZED_TRUCK = "specialized_truck"
    CUSTOM = "custom"


class TransportationMode(Enum):
    """Transportation modes supported"""
    ROAD = "road"
    RAIL = "rail"
    WATER = "water"
    CUSTOM = "custom"


@dataclass
class VehicleTemplate:
    """
    Represents a standard vehicle type with default capacities and attributes.
    Vehicles should always have a template type for reference.
    """
    vehicle_type: VehicleType
    name: str
    inventory_slots: int = 0
    crate_capacity: int = 0
    shippable_capacity: int = 0
    max_units: int = 1  # For trains, max number of cars
    description: str = ""
    
    def get_total_capacity(self) -> Dict[str, int]:
        """Return total capacity for different storage types"""
        return {
            "inventory_slots": self.inventory_slots,
            "crates": self.crate_capacity,
            "shippables": self.shippable_capacity
        }


@dataclass
class CustomVehicle:
    """
    Allows users to define custom vehicles, extending or overriding template defaults.
    """
    template: VehicleTemplate
    custom_name: str = ""
    custom_inventory_slots: Optional[int] = None
    custom_crate_capacity: Optional[int] = None
    custom_shippable_capacity: Optional[int] = None
    custom_max_units: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_effective_capacity(self) -> Dict[str, int]:
        """Get the effective capacity using custom overrides if provided"""
        return {
            "inventory_slots": self.custom_inventory_slots or self.template.inventory_slots,
            "crates": self.custom_crate_capacity or self.template.crate_capacity,
            "shippables": self.custom_shippable_capacity or self.template.shippable_capacity,
            "max_units": self.custom_max_units or self.template.max_units
        }


@dataclass
class Route:
    """
    Represents a path between two nodes with transportation options and time estimates.
    """
    source_node_id: str
    target_node_id: str
    allowed_vehicle_types: List[VehicleType] = field(default_factory=list)
    transportation_modes: Dict[TransportationMode, Dict[str, Any]] = field(default_factory=dict)
    regular_vehicle_time: Optional[float] = None  # Time in hours for standard vehicles
    flatbed_time: Optional[float] = None  # Time in hours for flatbed vehicles
    custom_times: Dict[str, float] = field(default_factory=dict)  # Custom vehicle times
    user_config: Dict[str, Any] = field(default_factory=dict)
    
    def get_transport_time(self, vehicle_type: VehicleType) -> Optional[float]:
        """Get transportation time for a specific vehicle type"""
        # First check for vehicle-specific custom times
        vehicle_name = vehicle_type.value
        if vehicle_name in self.custom_times:
            return self.custom_times[vehicle_name]
            
        # Then check for standard vehicle type times
        if vehicle_type == VehicleType.FLATBED and self.flatbed_time is not None:
            return self.flatbed_time
        elif self.regular_vehicle_time is not None:
            return self.regular_vehicle_time
        else:
            return None


class NetworkDecisionEngine:
    """
    Evaluates whether to transport or produce locally, factoring in times,
    surplus, knock-on effects, and fallback logic.
    """
    
    def __init__(self, enable_transportation: bool = True):
        """
        Initialize the decision engine.
        
        Args:
            enable_transportation: If False, defaults to production-only logic
        """
        self.enable_transportation = enable_transportation
        self.vehicle_templates = self._create_default_templates()
        self.routes: Dict[Tuple[str, str], Route] = {}
        
    def _create_default_templates(self) -> Dict[VehicleType, VehicleTemplate]:
        """Create default vehicle templates based on documentation"""
        templates = {
            VehicleType.FLATBED_TRAIN: VehicleTemplate(
                vehicle_type=VehicleType.FLATBED_TRAIN,
                name="Flatbed Train",
                shippable_capacity=1,  # 1 shippable per car
                max_units=15,  # Max 15 cars including locomotive
                description="Train with flatbed cars for shippables"
            ),
            VehicleType.FREIGHTER: VehicleTemplate(
                vehicle_type=VehicleType.FREIGHTER,
                name="Freighter",
                shippable_capacity=5,
                crate_capacity=10,
                description="Naval vessel for bulk transport"
            ),
            VehicleType.FLATBED: VehicleTemplate(
                vehicle_type=VehicleType.FLATBED,
                name="BMS Packmule",
                shippable_capacity=1,
                inventory_slots=1,
                description="Flatbed truck for shippables"
            ),
            VehicleType.BASE_TRUCK: VehicleTemplate(
                vehicle_type=VehicleType.BASE_TRUCK,
                name="R-5 Hauler / Dunne Transport",
                inventory_slots=15,
                description="Standard truck for general transport"
            ),
            VehicleType.SPECIALIZED_TRUCK: VehicleTemplate(
                vehicle_type=VehicleType.SPECIALIZED_TRUCK,
                name="Dunne Landrunner",
                inventory_slots=14,
                description="Specialized truck variant"
            )
        }
        return templates
        
    def add_route(self, route: Route) -> None:
        """Add a transportation route to the network"""
        route_key = (route.source_node_id, route.target_node_id)
        self.routes[route_key] = route
        
    def get_route(self, source_id: str, target_id: str) -> Optional[Route]:
        """Get route between two nodes"""
        return self.routes.get((source_id, target_id))
        
    def should_transport_vs_produce(
        self,
        item: str,
        quantity: int,
        source_id: str,
        target_id: str,
        production_time: Optional[float] = None,
        current_surplus: int = 0,
        vehicle_type: VehicleType = VehicleType.BASE_TRUCK
    ) -> Dict[str, Any]:
        """
        Decide whether to transport from source or produce locally at target.
        
        Args:
            item: Item type to transport/produce
            quantity: Amount needed
            source_id: Source node ID
            target_id: Target node ID  
            production_time: Local production time in hours (if available)
            current_surplus: Current surplus inventory at source
            vehicle_type: Vehicle type to use for transport
            
        Returns:
            Decision dict with recommendation and analysis
        """
        if not self.enable_transportation:
            return {
                "decision": "produce",
                "reason": "Transportation disabled - using production-only logic",
                "transport_time": None,
                "production_time": production_time,
                "confidence": 1.0
            }
            
        route = self.get_route(source_id, target_id)
        if not route:
            return {
                "decision": "produce",
                "reason": "No transportation route configured",
                "transport_time": None,
                "production_time": production_time,
                "confidence": 0.8
            }
            
        transport_time = route.get_transport_time(vehicle_type)
        if transport_time is None:
            return {
                "decision": "produce", 
                "reason": "No transportation time data available for route",
                "transport_time": None,
                "production_time": production_time,
                "confidence": 0.7
            }
            
        # Calculate effective transport time considering surplus
        effective_transport_time = self._calculate_effective_transport_time(
            transport_time, quantity, current_surplus
        )
        
        # Compare with production time if available
        if production_time is not None:
            if effective_transport_time < production_time:
                decision = "transport"
                reason = f"Transport ({effective_transport_time:.1f}h) faster than production ({production_time:.1f}h)"
                confidence = 0.9
            else:
                decision = "produce"
                reason = f"Production ({production_time:.1f}h) faster than transport ({effective_transport_time:.1f}h)"
                confidence = 0.9
        else:
            # No production time available - default to transport if route exists
            decision = "transport"
            reason = "No production time data - defaulting to transport"
            confidence = 0.6
            
        return {
            "decision": decision,
            "reason": reason,
            "transport_time": effective_transport_time,
            "production_time": production_time,
            "confidence": confidence,
            "surplus_adjustment": current_surplus > 0
        }
        
    def _calculate_effective_transport_time(
        self,
        base_transport_time: float,
        quantity_needed: int,
        current_surplus: int
    ) -> float:
        """
        Calculate effective transportation time considering surplus inventory.
        If surplus exists, transportation time is reduced proportionally.
        """
        if current_surplus >= quantity_needed:
            # Surplus covers all needs - minimal transport time for immediate access
            return base_transport_time * 0.1
        elif current_surplus > 0:
            # Partial surplus - reduce transport time proportionally
            surplus_ratio = current_surplus / quantity_needed
            return base_transport_time * (1 - surplus_ratio * 0.8)
        else:
            # No surplus - full transport time
            return base_transport_time
            
    def calculate_capacity_efficiency(
        self,
        vehicle_type: VehicleType,
        items_to_transport: Dict[str, int],
        item_storage_types: Dict[str, str]  # item -> "inventory"|"crate"|"shippable"
    ) -> Dict[str, Any]:
        """
        Calculate how efficiently a vehicle can transport the requested items.
        
        Args:
            vehicle_type: Type of vehicle to analyze
            items_to_transport: Dict of item -> quantity
            item_storage_types: Dict mapping items to their storage type
            
        Returns:
            Analysis of capacity efficiency
        """
        template = self.vehicle_templates.get(vehicle_type)
        if not template:
            return {"error": "Unknown vehicle type"}
            
        capacity = template.get_total_capacity()
        
        # Calculate space needed by storage type
        space_needed = {"inventory_slots": 0, "crates": 0, "shippables": 0}
        
        for item, qty in items_to_transport.items():
            storage_type = item_storage_types.get(item, "inventory_slots")
            if storage_type == "inventory":
                space_needed["inventory_slots"] += qty
            elif storage_type == "crate":
                space_needed["crates"] += qty
            elif storage_type == "shippable":
                space_needed["shippables"] += qty
                
        # Calculate efficiency ratios
        efficiency = {}
        for storage_type, needed in space_needed.items():
            available = capacity[storage_type]
            if available > 0:
                efficiency[storage_type] = needed / available  # Remove min() to allow >1.0
            else:
                efficiency[storage_type] = 0.0 if needed == 0 else float('inf')  # No capacity available
                
        overall_efficiency = max(efficiency.values()) if efficiency else 0.0
        
        return {
            "vehicle_type": vehicle_type.value,
            "capacity": capacity,
            "space_needed": space_needed,
            "efficiency_by_type": efficiency,
            "overall_efficiency": overall_efficiency,
            "can_transport": all(
                space_needed[t] <= capacity[t] 
                for t in space_needed
            )
        }


def create_default_decision_engine(enable_transportation: bool = True) -> NetworkDecisionEngine:
    """
    Create a default decision engine with standard configuration.
    
    Args:
        enable_transportation: Whether to enable transportation features
        
    Returns:
        Configured NetworkDecisionEngine instance
    """
    return NetworkDecisionEngine(enable_transportation=enable_transportation)


def add_standard_routes_example(engine: NetworkDecisionEngine) -> None:
    """
    Example function showing how to add standard routes to the decision engine.
    This would typically be configured by users based on their specific map/setup.
    """
    # Example route from depot to frontline
    depot_to_front = Route(
        source_node_id="main_depot",
        target_node_id="frontline_depot",
        allowed_vehicle_types=[VehicleType.BASE_TRUCK, VehicleType.FLATBED],
        regular_vehicle_time=2.5,  # 2.5 hours
        flatbed_time=3.0,  # 3 hours (slower but more capacity)
        user_config={"priority": "high", "notes": "Main supply line"}
    )
    
    # Example rail route
    rail_route = Route(
        source_node_id="factory_complex",
        target_node_id="staging_area", 
        allowed_vehicle_types=[VehicleType.FLATBED_TRAIN],
        custom_times={"flatbed_train": 1.5},  # 1.5 hours by rail
        user_config={"mode": "rail", "notes": "Bulk transport line"}
    )
    
    engine.add_route(depot_to_front)
    engine.add_route(rail_route)


# Example usage and integration functions
def integrate_with_inventory_edge(edge_user_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper function to integrate transportation cost data with InventoryEdge user_config.
    
    Args:
        edge_user_config: Existing user_config from InventoryEdge
        
    Returns:
        Updated user_config with transportation cost integration
    """
    # Add transportation cost configuration to existing edge config
    transportation_config = {
        "transportation_enabled": edge_user_config.get("transportation_enabled", False),
        "vehicle_types": edge_user_config.get("vehicle_types", [VehicleType.BASE_TRUCK.value]),
        "transport_times": edge_user_config.get("transport_times", {}),
        "capacity_limits": edge_user_config.get("capacity_limits", {})
    }
    
    # Merge with existing config
    updated_config = edge_user_config.copy()
    updated_config["transportation_cost"] = transportation_config
    
    return updated_config


if __name__ == "__main__":
    # Example usage
    print("Transportation Cost Algorithm - Example Usage")
    
    # Create decision engine
    engine = create_default_decision_engine(enable_transportation=True)
    
    # Add example routes
    add_standard_routes_example(engine)
    
    # Test decision making
    decision = engine.should_transport_vs_produce(
        item="rifle",
        quantity=50,
        source_id="main_depot",
        target_id="frontline_depot",
        production_time=4.0,  # 4 hours to produce locally
        current_surplus=10,   # 10 rifles already available
        vehicle_type=VehicleType.BASE_TRUCK
    )
    
    print(f"Decision: {decision}")
    
    # Test capacity efficiency
    items = {"rifle": 30, "ammo": 100}
    storage_types = {"rifle": "inventory", "ammo": "inventory"}
    
    efficiency = engine.calculate_capacity_efficiency(
        VehicleType.BASE_TRUCK,
        items,
        storage_types
    )
    
    print(f"Capacity efficiency: {efficiency}")