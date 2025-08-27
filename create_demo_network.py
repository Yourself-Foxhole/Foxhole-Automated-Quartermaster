#!/usr/bin/env python3
"""
Demo script to create a sample Foxhole logistics network

This script creates a sample network to demonstrate the onboarding CLI functionality.
"""

from onboard_network import NetworkOnboardingCLI
from services.inventory.production_nodes import FactoryNode, MassProductionFactoryNode, RefineryNode
from services.inventory.facility_node import FacilityNode
from services.inventory.base_types import BaseType
from services.FoxholeDataObjects.processes import ProductionType, FacilityType


def create_demo_network():
    """Create a comprehensive demo network."""
    cli = NetworkOnboardingCLI()
    
    print("Creating demo Foxhole logistics network...")
    
    # 1. Create MPF
    mpf_id = cli._generate_node_id()
    mpf_node = MassProductionFactoryNode(
        node_id=mpf_id,
        location_name="Westgate Mass Production Factory",
        unit_size="crate",
        base_type=BaseType.PRODUCTION,
        production_type=ProductionType.MPF
    )
    mpf_node.metadata.update({
        "facility_type": "MPF",
        "description": "Main MPF for vehicle production",
        "hex": "Westgate",
        "frontline": False
    })
    cli.nodes[mpf_id] = mpf_node
    cli.graph.add_node(mpf_node)
    
    # 2. Create Refinery
    refinery_id = cli._generate_node_id()
    refinery_node = RefineryNode(
        node_id=refinery_id,
        location_name="Heartlands Basic Materials Refinery",
        unit_size="crate",
        base_type=BaseType.REFINERY,
        production_type=ProductionType.FACILITY,
        facility_type=FacilityType.REFINERY
    )
    refinery_node.metadata.update({
        "facility_type": "Refinery",
        "refinery_type": "Basic Materials Refinery",
        "description": "Produces BMats and EMats",
        "hex": "Heartlands",
        "frontline": False
    })
    cli.nodes[refinery_id] = refinery_node
    cli.graph.add_node(refinery_node)
    
    # 3. Create Factory
    factory_id = cli._generate_node_id()
    factory_node = FactoryNode(
        node_id=factory_id,
        location_name="Deadlands Arms Factory",
        unit_size="crate",
        base_type=BaseType.PRODUCTION,
        production_type=ProductionType.FACTORY
    )
    factory_node.metadata.update({
        "facility_type": "Factory",
        "factory_type": "Small Arms Factory",
        "description": "Frontline weapons production",
        "hex": "Deadlands",
        "frontline": True
    })
    cli.nodes[factory_id] = factory_node
    cli.graph.add_node(factory_node)
    
    # 4. Create Storage Depot
    depot_id = cli._generate_node_id()
    depot_node = FacilityNode(
        node_id=depot_id,
        location_name="Westgate Supply Depot",
        unit_size="crate",
        base_type=BaseType.FACILITY,
        production_type=ProductionType.FACILITY
    )
    depot_node.metadata.update({
        "facility_type": "Storage Depot",
        "description": "Main supply depot",
        "hex": "Westgate",
        "frontline": False
    })
    cli.nodes[depot_id] = depot_node
    cli.graph.add_node(depot_node)
    
    # 5. Create Seaport
    seaport_id = cli._generate_node_id()
    seaport_node = FacilityNode(
        node_id=seaport_id,
        location_name="Fisherman's Row Seaport",
        unit_size="crate",
        base_type=BaseType.FACILITY,
        production_type=ProductionType.FACILITY
    )
    seaport_node.metadata.update({
        "facility_type": "Seaport",
        "description": "Maritime logistics hub",
        "hex": "Fisherman's Row",
        "frontline": False
    })
    cli.nodes[seaport_id] = seaport_node
    cli.graph.add_node(seaport_node)
    
    # 6. Create connections
    # Refinery -> MPF (basic materials)
    cli.graph.add_edge(refinery_id, mpf_id, allowed_items=["bmats", "emats", "refined_materials"])
    
    # MPF -> Depot (vehicles and equipment)
    cli.graph.add_edge(mpf_id, depot_id, allowed_items=["vehicles", "heavy_equipment", "uniforms"])
    
    # Refinery -> Factory (materials for weapons)
    cli.graph.add_edge(refinery_id, factory_id, allowed_items=["bmats", "emats"])
    
    # Factory -> Depot (weapons and ammo)
    cli.graph.add_edge(factory_id, depot_id, allowed_items=["rifles", "ammo", "explosives"])
    
    # Depot -> Seaport (shipments)
    cli.graph.add_edge(depot_id, seaport_id, allowed_items=["all_supplies"])
    
    # Seaport -> Factory (imported materials)
    cli.graph.add_edge(seaport_id, factory_id, allowed_items=["specialty_materials", "components"])
    
    print(f"✅ Created demo network with {len(cli.nodes)} nodes and {len(cli.graph.edges)} connections")
    
    return cli


def main():
    """Main demo function."""
    print("=" * 60)
    print("Foxhole Logistics Network - Demo Creation")
    print("=" * 60)
    
    # Create demo network
    cli = create_demo_network()
    
    # Show summary
    cli._show_network_summary()
    
    # Save as YAML
    print("\nSaving demo network as YAML...")
    cli._save_yaml("demo_foxhole_network.yaml")
    print("✅ Saved as: demo_foxhole_network.yaml")
    
    # Save as JSON
    print("\nSaving demo network as JSON...")
    cli._save_json("demo_foxhole_network.json")
    print("✅ Saved as: demo_foxhole_network.json")
    
    print("\nDemo files created! You can now test:")
    print("  python3 onboard_network.py --load demo_foxhole_network.yaml")
    print("  python3 onboard_network.py --status demo_foxhole_network.yaml")


if __name__ == "__main__":
    main()