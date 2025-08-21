"""
Integration example showing how to use the fluid dynamics priority system
with existing production and inventory graphs.
"""
import sys
import os
sys.path.append('/home/runner/work/Foxhole-Automated-Quartermaster/Foxhole-Automated-Quartermaster')

import networkx as nx
from services.tasks import GraphTaskIntegrator
from services.inventory.inventory_graph import InventoryGraph, InventoryNode


def create_sample_production_graph():
    """Create a sample production graph to demonstrate integration."""
    # Create a simple production chain: Iron -> Steel -> Rifles
    graph = nx.DiGraph()
    
    # Add nodes with mock node objects
    class MockProductionNode:
        def __init__(self, name, category):
            self.name = name
            self.category = category
    
    iron_node = MockProductionNode("Iron Extraction", "resource")
    steel_node = MockProductionNode("Steel Production", "refined")
    rifle_node = MockProductionNode("Rifle Manufacturing", "product")
    ammo_node = MockProductionNode("Ammunition Production", "product")
    
    graph.add_node("iron", node=iron_node)
    graph.add_node("steel", node=steel_node)
    graph.add_node("rifles", node=rifle_node)
    graph.add_node("ammo", node=ammo_node)
    
    # Add dependencies (edges represent "provides input to")
    graph.add_edge("iron", "steel")    # Iron needed for steel
    graph.add_edge("steel", "rifles")  # Steel needed for rifles
    graph.add_edge("steel", "ammo")    # Steel needed for ammo too
    
    return graph


def create_sample_inventory_graph():
    """Create a sample inventory graph to demonstrate integration."""
    graph = InventoryGraph()
    
    # Create nodes representing different locations
    mine = InventoryNode("mine_1", "Iron Mine", unit_size="item")
    mine.inventory = {"iron_ore": 1000}
    mine.delta = {"iron_ore": -100}  # High demand
    mine.status = "ok"
    
    factory = InventoryNode("factory_1", "Steel Factory")
    factory.inventory = {"steel": 50}
    factory.delta = {"steel": -200}  # Very high demand
    factory.status = "critical"  # Low on supplies
    
    depot = InventoryNode("depot_1", "Frontline Depot")
    depot.inventory = {"rifles": 10, "ammo": 25}
    depot.delta = {"rifles": -50, "ammo": -100}  # High frontline demand
    depot.status = "low"
    
    graph.add_node(mine)
    graph.add_node(factory)
    graph.add_node(depot)
    
    # Add supply chain edges
    graph.add_edge("mine_1", "factory_1", allowed_items=["iron_ore"])
    graph.add_edge("factory_1", "depot_1", allowed_items=["steel", "rifles", "ammo"])
    
    return graph


def demonstrate_production_graph_integration():
    """Show how to integrate production graphs with priority system."""
    print("=" * 60)
    print("PRODUCTION GRAPH INTEGRATION DEMONSTRATION")
    print("=" * 60)
    
    # Create sample production graph
    prod_graph = create_sample_production_graph()
    
    # Set up integrator with custom priorities
    integrator = GraphTaskIntegrator()
    
    # Define priority weights for different production items
    priority_map = {
        "iron": 1.0,      # Basic resource
        "steel": 3.0,     # Important refined material
        "rifles": 5.0,    # High priority weapon
        "ammo": 6.0       # Critical ammunition
    }
    
    print("Creating tasks from production graph...")
    tasks = integrator.create_tasks_from_production_graph(prod_graph, priority_map)
    
    print(f"Created {len(tasks)} production tasks:")
    for task in tasks:
        print(f"  - {task.name} (Priority: {task.base_priority})")
    
    print("\nSimulating production blockages...")
    # Simulate iron extraction being blocked (resource shortage)
    integrator.mark_production_blocked("iron", "Resource depletion")
    
    # Simulate steel production also being blocked (facility damage)
    integrator.mark_production_blocked("steel", "Facility damaged by artillery")
    
    print("\nGenerating priority analysis...")
    recommendations = integrator.get_priority_recommendations(10)
    
    print(f"\n{'Rank':<5} {'Node':<10} {'Task':<25} {'Priority':<10} {'Details'}")
    print("-" * 70)
    
    for i, (node_id, task_name, priority, details) in enumerate(recommendations):
        blocked_count = details.get("blocked_count", 0)
        print(f"{i+1:<5} {node_id:<10} {task_name:<25} {priority:<10.2f} {blocked_count} blocked upstream")
    
    print("\n" + integrator.generate_priority_report())


def demonstrate_inventory_graph_integration():
    """Show how to integrate inventory graphs with priority system."""
    print("\n" + "=" * 60)
    print("INVENTORY GRAPH INTEGRATION DEMONSTRATION")
    print("=" * 60)
    
    # Create sample inventory graph
    inv_graph = create_sample_inventory_graph()
    
    # Set up integrator
    integrator = GraphTaskIntegrator()
    
    print("Creating tasks from inventory graph...")
    tasks = integrator.create_tasks_from_inventory_graph(inv_graph)
    
    print(f"Created {len(tasks)} supply tasks:")
    for task in tasks:
        print(f"  - {task.name} (Priority: {task.base_priority:.2f}, Status: {task.status.value})")
    
    print("\nAnalyzing supply chain priorities...")
    recommendations = integrator.get_priority_recommendations(10)
    
    print(f"\n{'Rank':<5} {'Location':<15} {'Task':<25} {'Priority':<10}")
    print("-" * 60)
    
    for i, (node_id, task_name, priority, details) in enumerate(recommendations):
        print(f"{i+1:<5} {node_id:<15} {task_name:<25} {priority:<10.2f}")
    
    print("\n" + integrator.generate_priority_report())


def demonstrate_combined_scenario():
    """Show a combined scenario with both production and inventory issues."""
    print("\n" + "=" * 60)
    print("COMBINED SCENARIO: PRODUCTION + INVENTORY CRISIS")
    print("=" * 60)
    
    integrator = GraphTaskIntegrator()
    
    # Set up production graph
    prod_graph = create_sample_production_graph()
    priority_map = {"iron": 1.0, "steel": 3.0, "rifles": 5.0, "ammo": 6.0}
    prod_tasks = integrator.create_tasks_from_production_graph(prod_graph, priority_map)
    
    # Set up inventory graph
    inv_graph = create_sample_inventory_graph()
    inv_tasks = integrator.create_tasks_from_inventory_graph(inv_graph)
    
    print(f"Integrated system with {len(prod_tasks)} production + {len(inv_tasks)} supply tasks")
    
    # Simulate multiple crises
    print("\nSimulating multiple simultaneous crises:")
    print("1. Iron mine flooded (production blocked)")
    print("2. Steel factory under artillery fire (production blocked)")
    print("3. Factory already critically low on supplies")
    
    integrator.mark_production_blocked("iron", "Mine flooded")
    integrator.mark_production_blocked("steel", "Under artillery fire")
    
    print("\nFluid dynamics priority analysis results:")
    print("(Higher priority = more urgent due to blocking pressure)")
    
    recommendations = integrator.get_priority_recommendations(8)
    
    print(f"\n{'Priority':<10} {'Type':<12} {'Issue':<30} {'Recommendation'}")
    print("-" * 75)
    
    for i, (node_id, task_name, priority, details) in enumerate(recommendations):
        task_id = integrator.node_to_task_map.get(node_id, "")
        task = integrator.priority_calc.get_task(task_id) if task_id else None
        
        if task:
            if "prod_" in task.task_id:
                task_type = "Production"
                if task.status.value == "blocked":
                    issue = f"Blocked: {task.metadata.get('block_reason', 'Unknown')}"
                    recommendation = "Unblock immediately - affects downstream"
                else:
                    blocked_count = details.get("blocked_count", 0)
                    if blocked_count > 0:
                        issue = f"Waiting on {blocked_count} blocked dependencies"
                        recommendation = "Will auto-resolve when dependencies unblock"
                    else:
                        issue = "No blocking issues"
                        recommendation = "Normal operation"
            else:
                task_type = "Supply"
                if task.status.value == "blocked":
                    issue = "Supply chain disrupted"
                    recommendation = "Emergency resupply needed"
                else:
                    issue = "Demand exceeds supply"
                    recommendation = "Increase production or find alternatives"
        else:
            task_type = "Unknown"
            issue = "Analysis unavailable"
            recommendation = "Manual investigation required"
        
        print(f"{priority:<10.2f} {task_type:<12} {issue:<30} {recommendation}")
    
    print(f"\n{'=' * 75}")
    print("KEY INSIGHTS FROM FLUID DYNAMICS ANALYSIS:")
    print("- Blocked upstream tasks create 'pressure' that elevates downstream priorities")
    print("- Multiple blockages compound the effect (like multiple dams)")
    print("- Time pressure increases urgency the longer blockages persist")
    print("- Supply chain disruptions get prioritized based on downstream impact")
    print("- The algorithm helps identify which bottlenecks to fix first for maximum relief")


if __name__ == "__main__":
    demonstrate_production_graph_integration()
    demonstrate_inventory_graph_integration()
    demonstrate_combined_scenario()