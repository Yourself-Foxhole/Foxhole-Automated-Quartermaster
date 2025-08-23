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
    
    salvage_node = MockProductionNode("Salvage Processing", "resource")
    rmats_node = MockProductionNode("Refined Materials Production", "refined")
    blakerow_node = MockProductionNode("Blakerow 871 Manufacturing", "product")
    ammo_node = MockProductionNode("7.62 mm Ammo Production", "product")
    
    graph.add_node("salvage", node=salvage_node)
    graph.add_node("rmats", node=rmats_node)
    graph.add_node("blakerow", node=blakerow_node)
    graph.add_node("ammo762", node=ammo_node)
    
    # Add dependencies (edges represent "provides input to")
    graph.add_edge("salvage", "rmats")    # Salvage needed for refined materials
    graph.add_edge("rmats", "blakerow")   # Refined materials needed for rifles
    graph.add_edge("rmats", "ammo762")    # Refined materials needed for ammo too
    
    return graph


def create_sample_inventory_graph():
    """Create a sample inventory graph to demonstrate integration."""
    graph = InventoryGraph()
    
    # Create nodes representing different locations
    mine = InventoryNode("mine_1", "Iron Mine", unit_size="item")
    mine.inventory = {"salvage": 1000}
    mine.delta = {"salvage": -100}  # High demand
    mine.status = "ok"
    
    factory = InventoryNode("factory_1", "Steel Factory")
    factory.inventory = {"rmats": 50}
    factory.delta = {"rmats": -200}  # Very high demand
    factory.status = "critical"  # Low on supplies
    
    depot = InventoryNode("depot_1", "Frontline Depot")
    depot.inventory = {"blakerow": 10, "ammo762": 25}
    depot.delta = {"blakerow": -50, "ammo762": -100}  # High frontline demand
    depot.status = "low"
    
    graph.add_node(mine)
    graph.add_node(factory)
    graph.add_node(depot)
    
    # Add supply chain edges
    graph.add_edge("mine_1", "factory_1", allowed_items=["salvage"])
    graph.add_edge("factory_1", "depot_1", allowed_items=["rmats", "blakerow", "ammo762"])
    
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
        "salvage": 1.0,      # Basic resource
        "rmats": 3.0,        # Important refined material
        "blakerow": 5.0,     # High priority weapon
        "ammo762": 6.0       # Critical ammunition
    }
    
    print("Creating tasks from production graph...")
    tasks = integrator.create_tasks_from_production_graph(prod_graph, priority_map)
    
    print("Created {} production tasks:".format(len(tasks)))
    for task in tasks:
        print("  - {} (Priority: {})".format(task.name, task.base_priority))
    
    print("\nSimulating production blockages...")
    # Simulate salvage processing being blocked (resource shortage)
    integrator.mark_production_blocked("salvage", "Resource depletion")

    # Simulate rmats production also being blocked (facility damage)
    integrator.mark_production_blocked("rmats", "Facility damaged by artillery")
    
    print("\nGenerating priority analysis...")
    recommendations = integrator.get_priority_recommendations(10)
    
    print("\n{:<5} {:<10} {:<25} {:<10} {}".format("Rank", "Node", "Task", "Priority", "Details"))
    print("-" * 70)
    
    for i, (node_id, task_name, priority, details) in enumerate(recommendations):
        blocked_count = details.get("blocked_count", 0)
        print("{:<5} {:<10} {:<25} {:<10.2f} {} blocked upstream".format(i+1, node_id, task_name, priority, blocked_count))
    
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
    
    print("Created {} supply tasks:".format(len(tasks)))
    for task in tasks:
        print("  - {} (Priority: {}, Status: {})".format(task.name, round(task.base_priority, 2), task.status.value))
    
    print("\nAnalyzing supply chain priorities...")
    recommendations = integrator.get_priority_recommendations(10)
    
    print("\n{:<5} {:<15} {:<25} {:<10}".format("Rank", "Location", "Task", "Priority"))
    print("-" * 60)
    
    for i, (node_id, task_name, priority, details) in enumerate(recommendations):
        print("{:<5} {:<15} {:<25} {:<10.2f}".format(i+1, node_id, task_name, priority))
    
    print("\n" + integrator.generate_priority_report())


def demonstrate_combined_scenario():
    """Show a combined scenario with both production and inventory issues."""
    print("\n" + "=" * 60)
    print("COMBINED SCENARIO: PRODUCTION + INVENTORY CRISIS")
    print("=" * 60)
    
    integrator = GraphTaskIntegrator()
    
    # Set up production graph
    prod_graph = create_sample_production_graph()
    priority_map = {"salvage": 1.0, "rmats": 3.0, "blakerow": 5.0, "ammo762": 6.0}
    prod_tasks = integrator.create_tasks_from_production_graph(prod_graph, priority_map)
    
    # Set up inventory graph
    inv_graph = create_sample_inventory_graph()
    inv_tasks = integrator.create_tasks_from_inventory_graph(inv_graph)
    
    print("Integrated system with {} production + {} supply tasks".format(len(prod_tasks), len(inv_tasks)))
    
    # Simulate multiple crises
    print("\nSimulating multiple simultaneous crises:")
    print("1. Iron mine flooded (production blocked)")
    print("2. Steel factory under artillery fire (production blocked)")
    print("3. Factory already critically low on supplies")
    
    integrator.mark_production_blocked("salvage", "Mine flooded")
    integrator.mark_production_blocked("rmats", "Under artillery fire")
    
    print("\nFluid dynamics priority analysis results:")
    print("(Higher priority = more urgent due to blocking pressure)")
    
    recommendations = integrator.get_priority_recommendations(8)
    
    print("\n{:<10} {:<12} {:<30} {}".format("Priority", "Type", "Issue", "Recommendation"))
    print("-" * 75)
    
    for i, (node_id, task_name, priority, details) in enumerate(recommendations):
        task_id = integrator.node_to_task_map.get(node_id, "")
        task = integrator.priority_calc.get_task(task_id) if task_id else None
        
        if task:
            if "prod_" in task.task_id:
                task_type = "Production"
                if task.status.value == "blocked":
                    issue = "Blocked: {}".format(task.metadata.get("block_reason", "Unknown"))
                    recommendation = "Unblock immediately - affects downstream"
                else:
                    blocked_count = details.get("blocked_count", 0)
                    if blocked_count > 0:
                        issue = "Waiting on {} blocked dependencies".format(blocked_count)
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
        
        print("{:<10.2f} {:<12} {:<30} {}".format(priority, task_type, issue, recommendation))
    
    print("\n{}".format("=" * 75))
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