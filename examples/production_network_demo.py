"""
Production Network Demonstration

This example creates a complete production network with:
- Resource Node (Salvage)
- Refinery Node
- Source Storage Depot (Crates)
- Factory Node
- Destination Hex Storage Depot (Crates)
- Item Node

The network produces Basic Materials from Salvage, then converts them to Soldier's Supplies.
Target: 3000 Basic Materials and 200 Soldier's Supplies at the front.
"""


from services.inventory.production_nodes import (
    BaseNode, BaseType, ProductionNode, RefineryNode, FactoryNode
)
from services.inventory.resource_node import ResourceNode
from services.inventory.storage_node import StorageNode
from services.FoxholeDataObjects.processes import ProductionType, FacilityType, ProcessType


def build_network():
    """
    Build the node graph and connect nodes via edges (front to back).
    """
    salvage_node = ResourceNode(
        node_id="resource_001",
        location_name="Salvage Fields",
        unit_size="item"
    )
    refinery_node = RefineryNode(
        node_id="refinery_001",
        location_name="Refinery",
        unit_size="crate",
        production_type=ProductionType.FACILITY,
        facility_type=FacilityType.REFINERY,
        process_label="Resource::Refinery"
    )
    source_depot = StorageNode(
        node_type="crate",
        node_id="depot_001",
        location_name="Backline Depot",
        unit_size="crate"
    )
    factory_node = FactoryNode(
        node_id="factory_001",
        location_name="Backline Factory",
        unit_size="crate",
        production_type=ProductionType.FACTORY,
        process_label="Medical::Factory"
    )
    destination_depot = StorageNode(
        node_type="crate",
        node_id="depot_002",
        location_name="Frontline Depot",
        unit_size="crate"
    )
    frontline_node = StorageNode(
        node_type="item",
        node_id="frontline_001",
        location_name="Frontline Bunker Base",
        unit_size="item"
    )
    # Connect edges (front to back)
    frontline_node.add_edge(destination_depot)
    destination_depot.add_edge(source_depot)
    source_depot.add_edge(factory_node)
    source_depot.add_edge(refinery_node)
    factory_node.add_edge(source_depot)
    refinery_node.add_edge(salvage_node)
    return {
        "salvage_node": salvage_node,
        "refinery_node": refinery_node,
        "source_depot": source_depot,
        "factory_node": factory_node,
        "destination_depot": destination_depot,
        "frontline_node": frontline_node
    }

# Hardcoded process mapping for demo
PROCESS_MAP = {
    "Soldiers Supplies": "Medical::Factory",
    "Basic Materials": "Resource::Refinery"
}

# Hardcoded crate sizes for demo
CRATE_SIZES = {
    "Soldiers Supplies": 10,
    "Basic Materials": 100
}


def propagate_orders_from_front(node, desired_state):
    """
    Recursively propagate orders upstream and compute deltas.
    node: current node to process
    desired_state: dict of item -> quantity (only for ItemNode/frontline)
    """
    # If this is the frontline node, set desired state and create orders for missing items
    node.delta = desired_state.copy()
    for item, qty in desired_state.items():
        current = node.inventory.get(item, 0)
        missing = max(qty - current, 0)
        if missing > 0:
            for upstream in node.edges:
                # Place order for missing items as crates
                crate_item = f"{item} Crate" if item in CRATE_SIZES else item
                num_crates = (missing + CRATE_SIZES.get(item, 1) - 1) // CRATE_SIZES.get(item, 1)
                if not hasattr(upstream, 'order_table'):
                    upstream.order_table = []
                upstream.order_table.append({"item": crate_item, "quantity": num_crates, "status": "pending"})
                upstream.compute_delta_from_orders()
                propagate_orders_crate(upstream, crate_item, num_crates)


def propagate_orders_crate(node, crate_item, num_crates):
    """
    Propagate crate orders upstream recursively.
    """
    # If this is a crate node, propagate orders for crates upstream
    node.compute_delta_from_orders()
    for upstream in node.edges:
        # If upstream is a factory/refinery, check if it supports the process
        if hasattr(upstream, 'process_label'):
            # Map crate to item
            item = crate_item.replace(" Crate", "")
            process = PROCESS_MAP.get(item)
            if process and upstream.process_label == process:
                # Place production order for crates
                if not hasattr(upstream, 'production_queue'):
                    upstream.production_queue = {}
                if "auto" not in upstream.production_queue:
                    upstream.production_queue["auto"] = []
                upstream.production_queue["auto"].append({"item": item, "quantity": num_crates * CRATE_SIZES.get(item, 1), "process_label": process})
                upstream.compute_delta_from_orders()
                propagate_orders_production(upstream, item, num_crates * CRATE_SIZES.get(item, 1))
        else:
            # If upstream is another crate node, propagate further
            if not hasattr(upstream, 'order_table'):
                upstream.order_table = []
            upstream.order_table.append({"item": crate_item, "quantity": num_crates, "status": "pending"})
            upstream.compute_delta_from_orders()
            propagate_orders_crate(upstream, crate_item, num_crates)


def propagate_orders_production(node, item, quantity):
    """
    Propagate production orders upstream recursively.
    """
    node.compute_delta_from_orders()
    for upstream in node.edges:
        # For FactoryNode, calculate required input materials
        if node.process_label == "Medical::Factory" and item == "Soldiers Supplies":
            # Each crate is 10 supplies, each 10 requires 80 bmats
            num_crates = (quantity + 9) // 10
            bmats_needed = num_crates * 80
            if not hasattr(upstream, 'order_table'):
                upstream.order_table = []
            upstream.order_table.append({"item": "Basic Materials Crate", "quantity": (bmats_needed + 99) // 100, "status": "pending"})
            upstream.compute_delta_from_orders()
            propagate_orders_crate(upstream, "Basic Materials Crate", (bmats_needed + 99) // 100)
        elif node.process_label == "Resource::Refinery" and item == "Basic Materials":
            # Each crate is 100 bmats, each 1 bmat requires 2 salvage
            salvage_needed = quantity * 2
            for upstream2 in node.edges:
                if not hasattr(upstream2, 'order_table'):
                    upstream2.order_table = []
                upstream2.order_table.append({"item": "Salvage", "quantity": salvage_needed, "status": "pending"})
                upstream2.compute_delta_from_orders()


def production_requirements_analysis(nodes):
    """
    Analyze the propagated requirements and print:
    - Total salvage required
    - Production time for each item
    - Crate requirements
    """
    print("\n=== Production Requirements Analysis ===\n")
    # Salvage requirements
    salvage_node = nodes["salvage_node"]
    total_salvage = salvage_node.delta.get("Salvage", 0)
    print(f"Total Salvage Required: {total_salvage:,} units")

    # Refinery production time (Basic Materials)
    refinery_node = nodes["refinery_node"]
    bmats_to_produce = refinery_node.delta.get("Basic Materials", 0)
    refinery_recipe = {"input": {"Salvage": 2}, "output": {"Basic Materials": 1}, "cycle_time": 0.48}
    refinery_cycle_time = refinery_recipe["cycle_time"]
    refinery_time_minutes = (bmats_to_produce * refinery_cycle_time) / 60
    print(f"Refinery Production Time: {refinery_time_minutes:.1f} minutes for {bmats_to_produce:,} Basic Materials")

    # Factory production time (Soldiers Supplies)
    factory_node = nodes["factory_node"]
    supplies_to_produce = factory_node.delta.get("Soldiers Supplies", 0)
    factory_recipe = {"input": {"Basic Materials": 80}, "output": {"Soldiers Supplies": 10}, "cycle_time": 80, "crate_size": 10}
    factory_cycle_time = factory_recipe["cycle_time"]
    supplies_per_cycle = factory_recipe["output"]["Soldiers Supplies"]
    factory_cycles_needed = (supplies_to_produce + supplies_per_cycle - 1) // supplies_per_cycle
    factory_time_minutes = (factory_cycles_needed * factory_cycle_time) / 60
    print(f"Factory Production Time: {factory_time_minutes:.1f} minutes for {supplies_to_produce} Soldier's Supplies ({factory_cycles_needed} cycles)")

    # Crate calculations
    source_depot = nodes["source_depot"]
    destination_depot = nodes["destination_depot"]
    print(f"\nCrate Requirements:")
    print(f"  Basic Materials Crates (100 each): {source_depot.delta.get('Basic Materials Crate', 0)} crates (source depot)")
    print(f"  Soldiers Supplies Crates (10 each): {source_depot.delta.get('Soldiers Supplies Crate', 0)} crates (source depot)")
    print(f"  Basic Materials Crates (100 each): {destination_depot.delta.get('Basic Materials Crate', 0)} crates (frontline depot)")
    print(f"  Soldiers Supplies Crates (10 each): {destination_depot.delta.get('Soldiers Supplies Crate', 0)} crates (frontline depot)")

    # Total time estimate (assuming sequential production)
    total_time_hours = (refinery_time_minutes + factory_time_minutes) / 60
    print(f"\nTotal Production Time (sequential): {total_time_hours:.2f} hours")


def main():
    nodes = build_network()
    # Set desired state at the front
    desired_state = {"Basic Materials": 3000, "Soldiers Supplies": 200}
    propagate_orders_from_front(nodes["frontline_node"], desired_state)
    # Print out the order tables and deltas for each node
    for name, node in nodes.items():
        print(f"\n{name}: {node.location_name}")
        print(f"  Inventory: {node.inventory}")
        print(f"  Delta: {node.delta}")
        if hasattr(node, 'order_table'):
            print(f"  Orders: {getattr(node, 'order_table', [])}")
        if hasattr(node, 'production_queue'):
            print(f"  Production Queue: {getattr(node, 'production_queue', {})}")
    # Production requirements analysis
    production_requirements_analysis(nodes)

if __name__ == "__main__":
    main()
