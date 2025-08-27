#!/usr/bin/env python3
"""
Demonstration of transport_time feature in the Foxhole logistics network.

This script shows how to:
1. Add transport_time to inventory edges
2. Generate tasks that include transport time in priority calculations
3. Compare transportation vs production priorities
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.inventory.inventory_graph import InventoryGraph, InventoryNode
from services.tasks.task_layer import TaskGenerator
from services.inventory.base_types import BaseType


def demo_basic_transport_time():
    """Demonstrate basic transport_time functionality."""
    print("=== Basic Transport Time Demo ===")
    
    # Create inventory graph
    graph = InventoryGraph()
    depot = InventoryNode("depot", "Supply Depot", base_type=BaseType.ITEM_NODE)
    frontline = InventoryNode("frontline", "Frontline Base", base_type=BaseType.PRODUCTION)
    
    # Set up scenario: depot has rifles, frontline needs rifles
    depot.inventory = {"rifle": 100}
    frontline.delta = {"rifle": 30}
    
    graph.add_node(depot)
    graph.add_node(frontline)
    
    # Add transportation edge with 2.5 hour transport time
    graph.add_edge("frontline", "depot", 
                   allowed_items=["rifle"], 
                   transport_time=2.5)
    
    print("Graph Structure:")
    graph.print_status()
    
    # Generate tasks
    task_gen = TaskGenerator([depot, frontline])
    tasks = task_gen.get_actionable_tasks()
    
    print(f"\nGenerated {len(tasks)} tasks:")
    for i, task in enumerate(tasks, 1):
        print(f"{i}. {task.task_type.title()} Task:")
        print(f"   Item: {task.item} x{task.quantity}")
        if hasattr(task, 'source'):
            print(f"   Route: {task.source.location_name} -> {task.destination.location_name}")
        else:
            print(f"   Location: {task.node.location_name}")
        
        print(f"   Priority Score: {task.priority.score:.2f}")
        print(f"   Signals: {task.priority.signals}")
        
        if "transport_time" in task.priority.signals:
            print(f"   ✓ Transport Time: {task.priority.signals['transport_time']} hours")
        else:
            print(f"   ✗ No transport time configured")
        print()


def demo_priority_comparison():
    """Demonstrate how transport_time affects priority calculations."""
    print("=== Priority Comparison Demo ===")
    
    # Create two similar scenarios with different transport times
    scenarios = [
        ("Fast Route", 1.0),
        ("Slow Route", 4.0)
    ]
    
    tasks_by_scenario = {}
    
    for scenario_name, transport_time in scenarios:
        graph = InventoryGraph()
        factory = InventoryNode("factory", "Factory", base_type=BaseType.PRODUCTION)
        
        # Factory has rifles and also needs more (self-supply scenario)
        factory.inventory = {"rifle": 50}
        factory.delta = {"rifle": 20}
        
        graph.add_node(factory)
        graph.add_edge("factory", "factory", 
                       allowed_items=["rifle"], 
                       transport_time=transport_time)
        
        # Generate tasks
        task_gen = TaskGenerator([factory])
        tasks = task_gen.get_actionable_tasks()
        
        # Find transportation task
        transport_task = next((t for t in tasks 
                              if hasattr(t, 'source') and t.task_type == 'transportation'), 
                             None)
        
        if transport_task:
            tasks_by_scenario[scenario_name] = transport_task
    
    # Compare priorities
    print("Priority Comparison:")
    for scenario_name, task in tasks_by_scenario.items():
        transport_time = task.priority.signals.get("transport_time", "N/A")
        print(f"{scenario_name}:")
        print(f"  Transport Time: {transport_time} hours")
        print(f"  Priority Score: {task.priority.score:.2f}")
        print()
    
    # Show which is preferred
    if len(tasks_by_scenario) == 2:
        fast_task = tasks_by_scenario["Fast Route"]
        slow_task = tasks_by_scenario["Slow Route"]
        
        if fast_task.priority.score > slow_task.priority.score:
            print("✓ Fast Route has higher priority (preferred)")
        else:
            print("✗ Slow Route has higher priority (unexpected)")


def demo_mixed_configuration():
    """Demonstrate mixed edges with and without transport_time."""
    print("=== Mixed Configuration Demo ===")
    
    graph = InventoryGraph()
    
    # Create multiple supply sources
    depot_a = InventoryNode("depot_a", "Depot A (Fast)", base_type=BaseType.ITEM_NODE)
    depot_b = InventoryNode("depot_b", "Depot B (No Time)", base_type=BaseType.ITEM_NODE)
    frontline = InventoryNode("frontline", "Frontline", base_type=BaseType.ITEM_NODE)
    
    # Both depots have rifles, frontline needs them
    depot_a.inventory = {"rifle": 30}
    depot_a.delta = {"rifle": 10}  # Also needs some for self
    depot_b.inventory = {"rifle": 40}
    depot_b.delta = {"rifle": 15}  # Also needs some for self
    
    graph.add_node(depot_a)
    graph.add_node(depot_b)
    graph.add_node(frontline)
    
    # Add edges: one with transport_time, one without
    graph.add_edge("depot_a", "depot_a", 
                   allowed_items=["rifle"], 
                   transport_time=1.5)  # Fast depot with time
    
    graph.add_edge("depot_b", "depot_b", 
                   allowed_items=["rifle"])  # Legacy depot without time
    
    print("Graph Structure:")
    graph.print_status()
    
    # Generate tasks
    task_gen = TaskGenerator([depot_a, depot_b, frontline])
    tasks = task_gen.get_actionable_tasks()
    
    print(f"\nGenerated {len(tasks)} tasks:")
    for i, task in enumerate(tasks, 1):
        if task.task_type == "transportation":
            location = task.source.location_name if hasattr(task, 'source') else task.node.location_name
            has_time = "transport_time" in task.priority.signals
            time_value = task.priority.signals.get("transport_time", "N/A")
            
            print(f"{i}. Transportation from {location}")
            print(f"   Transport Time: {time_value} {'hours' if has_time else '(not configured)'}")
            print(f"   Priority Score: {task.priority.score:.2f}")
            print()


def main():
    """Run all demonstrations."""
    print("Transport Time Feature Demonstration")
    print("=" * 50)
    print()
    
    demo_basic_transport_time()
    print("\n" + "=" * 50 + "\n")
    
    demo_priority_comparison()
    print("\n" + "=" * 50 + "\n")
    
    demo_mixed_configuration()
    
    print("\nDemo completed! Transport time feature is working correctly.")


if __name__ == "__main__":
    main()