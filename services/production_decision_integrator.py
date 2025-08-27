"""
Production Decision Integrator

Integrates transportation cost analysis with production calculations to make
optimal logistics decisions. This module combines the existing production
calculator with the new transportation cost algorithm.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import time

from transportation_cost import (
    VehicleType, NetworkDecisionEngine, Route, create_default_decision_engine
)
from services.inventory.inventory_graph import InventoryGraph, InventoryNode, InventoryEdge


@dataclass
class ProductionDecision:
    """
    Represents a production decision with transportation cost analysis.
    """
    item: str
    quantity: int
    source_node_id: str
    target_node_id: str
    decision: str  # "transport", "produce", or "mixed"
    primary_reason: str
    confidence: float
    
    # Transportation details
    transport_time: Optional[float] = None
    transport_vehicle: Optional[VehicleType] = None
    transport_efficiency: Optional[float] = None
    
    # Production details  
    production_time: Optional[float] = None
    production_materials: Optional[Dict[str, float]] = None
    
    # Alternative analysis
    alternatives: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []


class ProductionDecisionIntegrator:
    """
    Integrates transportation costs with production decisions for optimal logistics.
    """
    
    def __init__(self, 
                 inventory_graph: InventoryGraph,
                 enable_transportation: bool = True,
                 default_production_time_multiplier: float = 1.0):
        """
        Initialize the integrator.
        
        Args:
            inventory_graph: The inventory graph with nodes and edges
            enable_transportation: Whether to enable transportation cost analysis
            default_production_time_multiplier: Multiplier for estimated production times
        """
        self.inventory_graph = inventory_graph
        self.transportation_engine = create_default_decision_engine(enable_transportation)
        self.default_production_time_multiplier = default_production_time_multiplier
        self.enable_transportation = enable_transportation
        
        # Initialize routes from inventory graph edges with transportation config
        self._sync_routes_from_graph()
    
    def _sync_routes_from_graph(self):
        """
        Synchronize transportation routes from inventory graph edge configurations.
        """
        for edge in self.inventory_graph.get_edges():
            if edge.is_transportation_enabled():
                transport_config = edge.get_transportation_config()
                transport_times = transport_config.get("transport_times", {})
                
                # Create route with times from edge configuration
                route = Route(
                    source_node_id=edge.source.node_id,
                    target_node_id=edge.target.node_id,
                    regular_vehicle_time=transport_times.get("base_truck"),
                    flatbed_time=transport_times.get("flatbed"),
                    custom_times=transport_times
                )
                
                self.transportation_engine.add_route(route)
    
    def estimate_production_time(self, 
                               item: str, 
                               quantity: int, 
                               node_id: str,
                               base_time_per_unit: Optional[float] = None) -> Optional[float]:
        """
        Estimate production time for an item at a specific node.
        
        This is a simplified estimation. In a full implementation, this would
        integrate with the production calculator to get accurate times based
        on available materials, facility types, and production chains.
        
        Args:
            item: Item to produce
            quantity: Amount to produce
            node_id: Node where production would occur
            base_time_per_unit: Base time per unit (hours), if known
            
        Returns:
            Estimated production time in hours, or None if cannot produce
        """
        node = self.inventory_graph.get_node(node_id)
        if not node:
            return None
            
        # Simple estimation based on item type and quantity
        # In reality, this would query the production calculator
        if base_time_per_unit is None:
            # Default time estimates (placeholder values)
            time_estimates = {
                "rifle": 0.1,      # 6 minutes per rifle
                "ammo": 0.05,      # 3 minutes per ammo stack
                "bmats": 0.02,     # Basic materials are fast
                "emats": 0.1,      # Explosive materials take longer
                "heavy_tank": 2.0, # Heavy equipment takes much longer
                "artillery_shell": 0.5
            }
            base_time_per_unit = time_estimates.get(item, 0.25)  # Default 15 min
        
        total_time = base_time_per_unit * quantity * self.default_production_time_multiplier
        return total_time
    
    def get_current_surplus(self, item: str, node_id: str) -> int:
        """
        Get current surplus inventory for an item at a node.
        
        Args:
            item: Item type
            node_id: Node to check
            
        Returns:
            Surplus quantity available
        """
        node = self.inventory_graph.get_node(node_id)
        if not node:
            return 0
            
        current_inventory = node.inventory.get(item, 0)
        delta_needed = abs(node.delta.get(item, 0))  # How much is needed
        
        # Surplus is what's available beyond immediate needs
        surplus = max(0, current_inventory - delta_needed)
        return surplus
    
    def analyze_production_decision(self, 
                                 item: str,
                                 quantity: int,
                                 target_node_id: str,
                                 potential_sources: Optional[List[str]] = None,
                                 vehicle_preference: VehicleType = VehicleType.BASE_TRUCK,
                                 include_alternatives: bool = True) -> ProductionDecision:
        """
        Analyze whether to transport or produce an item, considering all options.
        
        Args:
            item: Item type needed
            quantity: Amount needed
            target_node_id: Where the item is needed
            potential_sources: List of potential source nodes, or None for auto-discovery
            vehicle_preference: Preferred vehicle type for transportation
            include_alternatives: Whether to analyze alternative options
            
        Returns:
            ProductionDecision with recommendation and analysis
        """
        if not self.enable_transportation:
            # Transportation disabled - always produce locally
            production_time = self.estimate_production_time(item, quantity, target_node_id)
            return ProductionDecision(
                item=item,
                quantity=quantity,
                source_node_id=target_node_id,
                target_node_id=target_node_id,
                decision="produce",
                primary_reason="Transportation analysis disabled",
                confidence=1.0,
                production_time=production_time
            )
        
        # Find potential source nodes if not specified
        if potential_sources is None:
            potential_sources = self._find_potential_sources(item, target_node_id)
        
        # Analyze local production option
        local_production_time = self.estimate_production_time(item, quantity, target_node_id)
        
        # Analyze transportation options from each potential source
        transport_options = []
        for source_id in potential_sources:
            if source_id == target_node_id:
                continue  # Skip self
                
            surplus = self.get_current_surplus(item, source_id)
            
            transport_decision = self.transportation_engine.should_transport_vs_produce(
                item=item,
                quantity=quantity,
                source_id=source_id,
                target_id=target_node_id,
                production_time=local_production_time,
                current_surplus=surplus,
                vehicle_type=vehicle_preference
            )
            
            if transport_decision["decision"] == "transport":
                # Analyze capacity efficiency
                items_to_transport = {item: quantity}
                storage_types = {item: "inventory"}  # Simplified assumption
                
                efficiency = self.transportation_engine.calculate_capacity_efficiency(
                    vehicle_type=vehicle_preference,
                    items_to_transport=items_to_transport,
                    item_storage_types=storage_types
                )
                
                transport_options.append({
                    "source_id": source_id,
                    "transport_time": transport_decision["transport_time"],
                    "confidence": transport_decision["confidence"],
                    "efficiency": efficiency["overall_efficiency"],
                    "can_transport": efficiency["can_transport"],
                    "surplus_available": surplus,
                    "reason": transport_decision["reason"]
                })
        
        # Choose best option
        best_option = self._choose_best_option(
            local_production_time, transport_options, item, quantity
        )
        
        # Create decision object
        decision = ProductionDecision(
            item=item,
            quantity=quantity,
            source_node_id=best_option.get("source_id", target_node_id),
            target_node_id=target_node_id,
            decision=best_option["decision"],
            primary_reason=best_option["reason"],
            confidence=best_option["confidence"],
            transport_time=best_option.get("transport_time"),
            transport_vehicle=vehicle_preference if best_option["decision"] == "transport" else None,
            transport_efficiency=best_option.get("efficiency"),
            production_time=local_production_time
        )
        
        # Add alternatives if requested
        if include_alternatives:
            decision.alternatives = self._generate_alternatives(
                local_production_time, transport_options, best_option
            )
        
        return decision
    
    def _find_potential_sources(self, item: str, target_node_id: str) -> List[str]:
        """
        Find potential source nodes that could supply the item.
        
        Args:
            item: Item type
            target_node_id: Target node needing the item
            
        Returns:
            List of potential source node IDs
        """
        sources = []
        
        # Look for nodes with inventory of the item or edges that allow the item
        for node_id, node in self.inventory_graph.nodes.items():
            if node_id == target_node_id:
                continue
                
            # Check if node has inventory of the item
            if node.inventory.get(item, 0) > 0:
                sources.append(node_id)
            
            # Check if there's a route from this node to target that allows the item
            for edge in node.edges:
                if (edge.target.node_id == target_node_id and 
                    (not edge.allowed_items or item in edge.allowed_items)):
                    if node_id not in sources:
                        sources.append(node_id)
        
        return sources
    
    def _choose_best_option(self, 
                          local_production_time: Optional[float],
                          transport_options: List[Dict[str, Any]],
                          item: str,
                          quantity: int) -> Dict[str, Any]:
        """
        Choose the best option between local production and transportation.
        
        Returns:
            Dict describing the best option
        """
        # Filter to viable transport options (those that can actually transport)
        viable_transports = [opt for opt in transport_options if opt["can_transport"]]
        
        # If no options can transport fully, check if we have transport options with reasonable efficiency
        if not viable_transports:
            # Allow transport options that are over capacity but still reasonable (< 2x capacity)
            reasonable_transports = [opt for opt in transport_options if opt["efficiency"] < 2.0]
            if reasonable_transports:
                viable_transports = reasonable_transports
        
        if not viable_transports:
            # No viable transport options - produce locally
            return {
                "decision": "produce",
                "reason": "No viable transportation options available",
                "confidence": 0.8 if local_production_time else 0.6,
                "transport_time": None,
                "efficiency": None
            }
        
        # Sort transport options by effective time and efficiency
        viable_transports.sort(key=lambda x: (x["transport_time"], -x["efficiency"]))
        best_transport = viable_transports[0]
        
        if local_production_time is None:
            # Cannot produce locally - must transport
            return {
                "decision": "transport",
                "reason": f"Cannot produce locally - transport from {best_transport['source_id']}",
                "confidence": best_transport["confidence"],
                "source_id": best_transport["source_id"],
                "transport_time": best_transport["transport_time"],
                "efficiency": best_transport["efficiency"]
            }
        
        # Compare best transport with local production
        if best_transport["transport_time"] < local_production_time * 0.8:
            # Transport is significantly faster
            return {
                "decision": "transport",
                "reason": f"Transport ({best_transport['transport_time']:.1f}h) significantly faster than production ({local_production_time:.1f}h)",
                "confidence": min(0.95, best_transport["confidence"] + 0.1),
                "source_id": best_transport["source_id"],
                "transport_time": best_transport["transport_time"],
                "efficiency": best_transport["efficiency"]
            }
        elif best_transport["transport_time"] < local_production_time:
            # Transport is faster but not by much
            return {
                "decision": "transport",
                "reason": f"Transport ({best_transport['transport_time']:.1f}h) faster than production ({local_production_time:.1f}h)",
                "confidence": best_transport["confidence"],
                "source_id": best_transport["source_id"],
                "transport_time": best_transport["transport_time"],
                "efficiency": best_transport["efficiency"]
            }
        else:
            # Local production is faster or equivalent
            return {
                "decision": "produce",
                "reason": f"Local production ({local_production_time:.1f}h) faster than transport ({best_transport['transport_time']:.1f}h)",
                "confidence": 0.9
            }
    
    def _generate_alternatives(self, 
                             local_production_time: Optional[float],
                             transport_options: List[Dict[str, Any]],
                             chosen_option: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate alternative options not chosen as the primary decision.
        """
        alternatives = []
        
        # Add local production as alternative if not chosen
        if chosen_option["decision"] != "produce" and local_production_time:
            alternatives.append({
                "type": "local_production",
                "time": local_production_time,
                "reason": "Produce locally instead of transporting"
            })
        
        # Add other transport options as alternatives
        chosen_source = chosen_option.get("source_id")
        for opt in transport_options:
            if opt["source_id"] != chosen_source and opt["can_transport"]:
                alternatives.append({
                    "type": "transport",
                    "source_id": opt["source_id"],
                    "time": opt["transport_time"],
                    "efficiency": opt["efficiency"],
                    "reason": f"Transport from {opt['source_id']} instead"
                })
        
        return alternatives
    
    def batch_analyze_decisions(self, 
                              requests: List[Dict[str, Any]]) -> List[ProductionDecision]:
        """
        Analyze multiple production decisions in batch.
        
        Args:
            requests: List of request dicts with keys: item, quantity, target_node_id
            
        Returns:
            List of ProductionDecision objects
        """
        decisions = []
        
        for request in requests:
            decision = self.analyze_production_decision(
                item=request["item"],
                quantity=request["quantity"],
                target_node_id=request["target_node_id"],
                potential_sources=request.get("potential_sources"),
                vehicle_preference=request.get("vehicle_preference", VehicleType.BASE_TRUCK),
                include_alternatives=request.get("include_alternatives", True)
            )
            decisions.append(decision)
        
        return decisions


def create_integrated_system(inventory_graph: InventoryGraph,
                           enable_transportation: bool = True) -> ProductionDecisionIntegrator:
    """
    Create an integrated production decision system.
    
    Args:
        inventory_graph: Configured inventory graph
        enable_transportation: Whether to enable transportation cost analysis
        
    Returns:
        Configured ProductionDecisionIntegrator
    """
    return ProductionDecisionIntegrator(
        inventory_graph=inventory_graph,
        enable_transportation=enable_transportation
    )


if __name__ == "__main__":
    # Example usage
    from services.inventory.inventory_graph import InventoryGraph, InventoryNode
    
    print("Production Decision Integrator - Example Usage")
    
    # Create example inventory graph
    graph = InventoryGraph()
    
    # Add nodes
    depot = InventoryNode("depot", "Main Depot")
    depot.inventory = {"rifle": 100, "ammo": 500}
    depot.delta = {"rifle": -20, "ammo": -100}  # Surplus available
    
    factory = InventoryNode("factory", "Weapons Factory") 
    factory.inventory = {"bmats": 200}
    factory.delta = {"rifle": 30}  # Needs rifles
    
    frontline = InventoryNode("frontline", "Frontline Base")
    frontline.inventory = {"ammo": 50}
    frontline.delta = {"rifle": 75, "ammo": 200}  # High demand
    
    graph.add_node(depot)
    graph.add_node(factory)
    graph.add_node(frontline)
    
    # Add edges with transportation
    graph.add_edge("depot", "factory", allowed_items=["rifle", "ammo"])
    graph.add_edge("depot", "frontline", allowed_items=["rifle", "ammo"])
    graph.add_edge("factory", "frontline", allowed_items=["rifle"])
    
    # Configure transportation times
    depot_factory_edge = graph.edges[0]
    depot_factory_edge.set_transportation_config({
        "transportation_enabled": True,
        "transport_times": {"base_truck": 1.5}
    })
    
    depot_frontline_edge = graph.edges[1]
    depot_frontline_edge.set_transportation_config({
        "transportation_enabled": True,
        "transport_times": {"base_truck": 4.0, "flatbed": 4.5}
    })
    
    # Create integrated system
    integrator = create_integrated_system(graph, enable_transportation=True)
    
    # Analyze decisions
    decision = integrator.analyze_production_decision(
        item="rifle",
        quantity=50,
        target_node_id="frontline"
    )
    
    print(f"\nDecision Analysis:")
    print(f"Item: {decision.item} x{decision.quantity}")
    print(f"Target: {decision.target_node_id}")
    print(f"Decision: {decision.decision.upper()}")
    print(f"Source: {decision.source_node_id}")
    print(f"Reason: {decision.primary_reason}")
    print(f"Confidence: {decision.confidence:.1%}")
    print(f"Transport time: {decision.transport_time}h")
    print(f"Production time: {decision.production_time}h")
    
    if decision.alternatives:
        print(f"\nAlternatives:")
        for alt in decision.alternatives:
            print(f"- {alt['type']}: {alt['time']:.1f}h - {alt['reason']}")