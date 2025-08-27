#!/usr/bin/env python3
"""
Demonstration of Transportation Cost Integration with Foxhole Logistics Network

This example shows how to use the new transportation cost features with
the existing inventory graph system. The feature is completely optional
and defaults to production-only logic when not configured.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from transportation_cost import (
    VehicleType, VehicleTemplate, Route, NetworkDecisionEngine,
    create_default_decision_engine, integrate_with_inventory_edge
)
from services.inventory.inventory_graph import InventoryGraph, InventoryNode, InventoryEdge


def demo_basic_transportation_decisions():
    """
    Demonstrate basic transportation vs production decision making.
    """
    print("=" * 60)
    print("DEMO: Basic Transportation vs Production Decisions")
    print("=" * 60)
    
    # Create decision engine
    engine = create_default_decision_engine(enable_transportation=True)
    
    # Add a route between depot and frontline
    route = Route(
        source_node_id="main_depot",
        target_node_id="frontline_base",
        allowed_vehicle_types=[VehicleType.BASE_TRUCK, VehicleType.FLATBED],
        regular_vehicle_time=3.0,  # 3 hours by truck
        flatbed_time=3.5           # 3.5 hours by flatbed
    )
    engine.add_route(route)
    
    # Test scenarios
    scenarios = [
        {
            "name": "Fast Transport vs Slow Production",
            "item": "rifle",
            "quantity": 50,
            "source": "main_depot",
            "target": "frontline_base",
            "production_time": 6.0,
            "surplus": 0,
            "vehicle": VehicleType.BASE_TRUCK
        },
        {
            "name": "Slow Transport vs Fast Production",
            "item": "heavy_tank",
            "quantity": 2,
            "source": "main_depot", 
            "target": "frontline_base",
            "production_time": 1.5,
            "surplus": 0,
            "vehicle": VehicleType.FLATBED
        },
        {
            "name": "Transport with Surplus Available",
            "item": "ammo",
            "quantity": 100,
            "source": "main_depot",
            "target": "frontline_base", 
            "production_time": 4.0,
            "surplus": 60,  # 60% of need available
            "vehicle": VehicleType.BASE_TRUCK
        }
    ]
    
    for scenario in scenarios:
        print(f"\nScenario: {scenario['name']}")
        print(f"Item: {scenario['item']}, Quantity: {scenario['quantity']}")
        print(f"Production time: {scenario['production_time']}h, Surplus: {scenario['surplus']}")
        
        decision = engine.should_transport_vs_produce(
            item=scenario['item'],
            quantity=scenario['quantity'],
            source_id=scenario['source'],
            target_id=scenario['target'],
            production_time=scenario['production_time'],
            current_surplus=scenario['surplus'],
            vehicle_type=scenario['vehicle']
        )
        
        print(f"DECISION: {decision['decision'].upper()}")
        print(f"Reason: {decision['reason']}")
        print(f"Transport time: {decision['transport_time']}h")
        print(f"Confidence: {decision['confidence']:.1%}")
        if decision.get('surplus_adjustment'):
            print("Note: Transport time reduced due to available surplus")


def demo_vehicle_capacity_analysis():
    """
    Demonstrate vehicle capacity efficiency calculations.
    """
    print("\n" + "=" * 60)
    print("DEMO: Vehicle Capacity Analysis")
    print("=" * 60)
    
    engine = create_default_decision_engine()
    
    # Define different cargo loads
    cargo_scenarios = [
        {
            "name": "Light Infantry Equipment",
            "items": {"rifle": 15, "ammo": 30, "medical_kit": 5},
            "storage_types": {"rifle": "inventory", "ammo": "inventory", "medical_kit": "inventory"}
        },
        {
            "name": "Heavy Artillery Shells",
            "items": {"artillery_shell": 1},
            "storage_types": {"artillery_shell": "shippable"}
        },
        {
            "name": "Mixed Supply Crates",
            "items": {"bmats_crate": 8, "rifle_crate": 2},
            "storage_types": {"bmats_crate": "crate", "rifle_crate": "crate"}
        },
        {
            "name": "Overloaded Cargo",
            "items": {"rifle": 25, "ammo": 50},  # Exceeds 15 slot truck capacity
            "storage_types": {"rifle": "inventory", "ammo": "inventory"}
        }
    ]
    
    # Test different vehicle types
    vehicles_to_test = [VehicleType.BASE_TRUCK, VehicleType.FREIGHTER, VehicleType.FLATBED]
    
    for cargo in cargo_scenarios:
        print(f"\nCargo Load: {cargo['name']}")
        print(f"Items: {cargo['items']}")
        
        for vehicle in vehicles_to_test:
            efficiency = engine.calculate_capacity_efficiency(
                vehicle_type=vehicle,
                items_to_transport=cargo['items'],
                item_storage_types=cargo['storage_types']
            )
            
            print(f"\n  {vehicle.value.replace('_', ' ').title()}:")
            print(f"    Can transport: {'✓' if efficiency['can_transport'] else '✗'}")
            print(f"    Efficiency: {efficiency['overall_efficiency']:.1%}")
            
            if efficiency['overall_efficiency'] > 1.0:
                print(f"    ⚠️  Over capacity by {(efficiency['overall_efficiency'] - 1) * 100:.0f}%")


def demo_inventory_graph_integration():
    """
    Demonstrate integration with existing inventory graph system.
    """
    print("\n" + "=" * 60)
    print("DEMO: Integration with Inventory Graph")
    print("=" * 60)
    
    # Create inventory graph with transportation-enabled edges
    graph = InventoryGraph()
    
    # Create nodes
    depot = InventoryNode("main_depot", "Main Supply Depot")
    factory = InventoryNode("weapons_factory", "Weapons Factory")
    frontline = InventoryNode("frontline_base", "Frontline Base")
    
    graph.add_node(depot)
    graph.add_node(factory)
    graph.add_node(frontline)
    
    # Add edges with different transportation configurations
    graph.add_edge("main_depot", "weapons_factory", allowed_items=["bmats", "emats"])
    graph.add_edge("weapons_factory", "frontline_base", allowed_items=["rifle", "ammo"])
    graph.add_edge("main_depot", "frontline_base", allowed_items=["supplies"])
    
    # Configure transportation for depot -> factory (short distance)
    depot_factory_edge = graph.edges[0]
    depot_factory_edge.set_transportation_config({
        "transportation_enabled": True,
        "vehicle_types": ["base_truck"],
        "transport_times": {"base_truck": 1.5}  # 1.5 hours
    })
    
    # Configure transportation for factory -> frontline (medium distance)
    factory_frontline_edge = graph.edges[1]
    factory_frontline_edge.set_transportation_config({
        "transportation_enabled": True,
        "vehicle_types": ["base_truck", "flatbed"],
        "transport_times": {"base_truck": 3.0, "flatbed": 3.5}
    })
    
    # Leave depot -> frontline without transportation config (will default to production)
    depot_frontline_edge = graph.edges[2]
    # No transportation config = disabled by default
    
    print("Inventory Graph Configuration:")
    print("- Main Depot → Weapons Factory: Transportation enabled (1.5h)")
    print("- Weapons Factory → Frontline: Transportation enabled (3.0h truck, 3.5h flatbed)")
    print("- Main Depot → Frontline: Transportation disabled (production only)")
    
    # Test configuration queries
    print(f"\nEdge Configuration Tests:")
    print(f"Depot→Factory transportation enabled: {depot_factory_edge.is_transportation_enabled()}")
    print(f"Depot→Factory transport time: {depot_factory_edge.get_transport_time('base_truck')}h")
    
    print(f"Factory→Frontline transportation enabled: {factory_frontline_edge.is_transportation_enabled()}")
    print(f"Factory→Frontline truck time: {factory_frontline_edge.get_transport_time('base_truck')}h")
    print(f"Factory→Frontline flatbed time: {factory_frontline_edge.get_transport_time('flatbed')}h")
    
    print(f"Depot→Frontline transportation enabled: {depot_frontline_edge.is_transportation_enabled()}")
    print(f"Depot→Frontline transport time: {depot_frontline_edge.get_transport_time('base_truck')}")


def demo_disabled_transportation():
    """
    Demonstrate the optional nature of transportation features.
    """
    print("\n" + "=" * 60)
    print("DEMO: Optional Transportation Features")
    print("=" * 60)
    
    print("Testing transportation DISABLED (production-only mode):")
    
    # Create engine with transportation disabled
    disabled_engine = create_default_decision_engine(enable_transportation=False)
    
    decision = disabled_engine.should_transport_vs_produce(
        item="rifle",
        quantity=50,
        source_id="depot",
        target_id="frontline",
        production_time=4.0
    )
    
    print(f"Decision: {decision['decision']}")
    print(f"Reason: {decision['reason']}")
    print(f"Confidence: {decision['confidence']:.1%}")
    
    print("\nTesting transportation ENABLED but no route configured:")
    
    enabled_engine = create_default_decision_engine(enable_transportation=True)
    
    decision = enabled_engine.should_transport_vs_produce(
        item="rifle",
        quantity=50,
        source_id="depot",
        target_id="frontline",
        production_time=4.0
    )
    
    print(f"Decision: {decision['decision']}")
    print(f"Reason: {decision['reason']}")
    print(f"Confidence: {decision['confidence']:.1%}")


def demo_vehicle_templates():
    """
    Demonstrate the default vehicle templates and customization.
    """
    print("\n" + "=" * 60)
    print("DEMO: Vehicle Templates")
    print("=" * 60)
    
    engine = create_default_decision_engine()
    
    print("Default Vehicle Templates:")
    for vehicle_type, template in engine.vehicle_templates.items():
        capacity = template.get_total_capacity()
        print(f"\n{template.name} ({vehicle_type.value}):")
        print(f"  Inventory slots: {capacity['inventory_slots']}")
        print(f"  Crate capacity: {capacity['crates']}")
        print(f"  Shippable capacity: {capacity['shippables']}")
        if hasattr(template, 'max_units') and template.max_units > 1:
            print(f"  Max units: {template.max_units}")
        print(f"  Description: {template.description}")


def main():
    """Run all demonstration scenarios."""
    print("FOXHOLE LOGISTICS NETWORK - TRANSPORTATION COST FEATURE DEMO")
    print("This demonstrates the optional transportation cost algorithm integration.")
    
    demo_basic_transportation_decisions()
    demo_vehicle_capacity_analysis()
    demo_inventory_graph_integration()
    demo_disabled_transportation()
    demo_vehicle_templates()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("Key Features Demonstrated:")
    print("✓ Optional transportation cost calculations")
    print("✓ Transport vs production decision making")
    print("✓ Vehicle capacity efficiency analysis")
    print("✓ Integration with existing inventory graph")
    print("✓ Surplus inventory adjustments")
    print("✓ Fallback to production-only when disabled")
    print("✓ Configurable vehicle templates and routes")
    print("\nThe transportation cost feature is completely optional and defaults")
    print("to production-only logic when not configured or disabled.")


if __name__ == "__main__":
    main()