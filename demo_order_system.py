#!/usr/bin/env python3
"""
Demonstration of the Order Collection & Assignment System

This script demonstrates how the implemented order system works:
1. Collects orders from inventory graph deltas
2. Assigns orders to tasks
3. Weights priorities using fluid dynamics + order urgency
4. Shows actionable task recommendations
"""
import sys
import os
sys.path.append(os.path.abspath('.'))

from services.inventory.inventory_graph import InventoryGraph, InventoryNode
from services.inventory.order import OrderManager, OrderType, OrderStatus
from services.tasks import TaskOrderIntegrator, FluidDynamicsPriorityCalculator
from datetime import datetime, timedelta


def create_demo_inventory_graph():
    """Create a demo inventory graph with various shortages."""
    print("🏗️  Creating demo inventory graph with shortages...")
    
    graph = InventoryGraph()
    
    # Frontline depot with critical rifle shortage
    frontline_depot = InventoryNode("depot_front", "Frontline Depot")
    frontline_depot.inventory = {"rifle": 5, "ammo": 50}
    frontline_depot.delta = {"rifle": -45, "ammo": -150}  # Critical shortages
    frontline_depot.status = "critical"
    graph.add_node(frontline_depot)
    
    # Factory with material shortage
    munitions_factory = InventoryNode("factory_munitions", "Munitions Factory")
    munitions_factory.inventory = {"bmats": 20, "ammo": 200}
    munitions_factory.delta = {"bmats": -80, "ammo": 300}  # Need materials, producing ammo
    munitions_factory.status = "low"
    graph.add_node(munitions_factory)
    
    # Logistics hub with transport needs
    logistics_hub = InventoryNode("hub_logistics", "Central Logistics Hub")
    logistics_hub.inventory = {"rifle": 100, "ammo": 500, "bmats": 150}
    logistics_hub.delta = {"rifle": -25, "ammo": -100, "bmats": -30}  # Moderate shortages
    logistics_hub.status = "ok"
    graph.add_node(logistics_hub)
    
    # Resource node with extraction needs
    salvage_field = InventoryNode("resource_salvage", "Salvage Field Alpha")
    salvage_field.inventory = {"salvage": 1000}
    salvage_field.delta = {"salvage": -200}  # Extraction demand
    salvage_field.status = "ok"
    graph.add_node(salvage_field)
    
    print(f"   ✅ Created graph with {len(graph.nodes)} nodes")
    return graph


def demonstrate_order_collection(integrator, graph):
    """Demonstrate order collection from inventory graph."""
    print("\n📦 Collecting orders from inventory graph deltas...")
    
    # Process the graph to collect orders
    tasks = integrator.process_inventory_graph_orders(graph)
    
    # Show collected orders
    all_orders = list(integrator.order_manager.orders.values())
    print(f"   ✅ Collected {len(all_orders)} orders and created {len(tasks)} tasks")
    
    print("\n📋 Orders collected:")
    for order in all_orders:
        urgency_indicator = "🔥" if order.urgency > 3.0 else "⚠️" if order.urgency > 2.0 else "📌"
        print(f"   {urgency_indicator} {order.order_type.value.upper()}: {order.quantity}x {order.item_type}")
        print(f"      Location: {order.metadata.get('source_location', order.source_node_id)}")
        print(f"      Urgency: {order.urgency:.2f} | Status: {order.status.value}")
        print(f"      Order ID: {order.order_id}")
        print()
    
    return tasks, all_orders


def demonstrate_task_assignment(integrator, tasks):
    """Demonstrate task assignment and order mapping."""
    print("🎯 Task-Order Assignment:")
    
    for i, task in enumerate(tasks, 1):
        order_count = task.get_order_count()
        print(f"   Task {i}: {task.name}")
        print(f"   └── Type: {task.task_type} | Base Priority: {task.base_priority:.2f}")
        print(f"   └── Orders: {order_count} assigned")
        
        # Show assigned orders
        for order_id in task.associated_orders:
            order = integrator.order_manager.get_order(order_id)
            if order:
                print(f"       • {order.item_type} x{order.quantity} (urgency: {order.urgency:.2f})")
        print()


def demonstrate_priority_calculation(integrator):
    """Demonstrate priority calculation with order urgency."""
    print("🧮 Priority Calculation with Order Urgency:")
    
    rankings = integrator.get_priority_rankings_with_orders(top_n=10)
    
    print("\n🏆 Top Priority Tasks (with fluid dynamics + order urgency):")
    for i, (task_id, priority, details) in enumerate(rankings, 1):
        task = integrator.priority_calc.get_task(task_id)
        if task:
            priority_indicator = "🔴" if priority > 10 else "🟡" if priority > 5 else "🟢"
            print(f"   {i}. {priority_indicator} {task.name}")
            print(f"      Priority Score: {priority:.2f}")
            print(f"      └── Base: {details['base_priority']:.2f} | " +
                  f"Blocked: {details['total_weight']:.2f} | " +
                  f"Time: {details['time_multiplier']:.2f}x | " +
                  f"Orders: +{details['order_urgency_bonus']:.2f}")
            
            if details['associated_orders']:
                print(f"      └── Orders contributing urgency:")
                for order_detail in details['associated_orders']:
                    print(f"          • {order_detail['item_type']} x{order_detail['quantity']} " +
                          f"(urgency: {order_detail['urgency']:.2f})")
            print()


def simulate_blocking_and_urgency(integrator):
    """Simulate task blocking to show fluid dynamics in action."""
    print("⛔ Simulating task blocking to demonstrate fluid dynamics...")
    
    # Block a critical task
    task_list = list(integrator.priority_calc.task_graph.values())
    if task_list:
        blocked_task = task_list[0]
        blocked_task.mark_blocked()
        # Simulate it being blocked for a while
        blocked_task.blocked_since = datetime.utcnow() - timedelta(hours=3)
        
        print(f"   ⛔ Blocked task: {blocked_task.name} (blocked for 3 hours)")
        
        # Show how this affects priorities
        rankings = integrator.get_priority_rankings_with_orders(top_n=5)
        print("\n📈 Updated priorities after blocking:")
        
        for i, (task_id, priority, details) in enumerate(rankings, 1):
            task = integrator.priority_calc.get_task(task_id)
            if task:
                status_icon = "⛔" if task.status.value == "blocked" else "▶️"
                print(f"   {i}. {status_icon} {task.name} - Priority: {priority:.2f}")
                if details['blocked_count'] > 0:
                    print(f"      └── Fluid pressure from {details['blocked_count']} blocked upstream tasks")


def demonstrate_order_lifecycle(integrator):
    """Demonstrate order lifecycle management."""
    print("\n♻️  Order Lifecycle Management:")
    
    all_orders = list(integrator.order_manager.orders.values())
    if all_orders:
        # Complete one order
        test_order = all_orders[0]
        print(f"   ✅ Completing order: {test_order.order_id} ({test_order.item_type})")
        integrator.complete_order(test_order.order_id)
        
        # Cancel another order
        if len(all_orders) > 1:
            cancel_order = all_orders[1]
            print(f"   ❌ Cancelling order: {cancel_order.order_id} ({cancel_order.item_type})")
            integrator.cancel_order(cancel_order.order_id, "Supply route compromised")


def show_integration_summary(integrator):
    """Show final integration summary."""
    print("\n📊 Integration Summary:")
    
    summary = integrator.get_integration_summary()
    
    print(f"   📈 System Overview:")
    print(f"      • Total Tasks: {summary['total_tasks']}")
    print(f"      • Order-Driven Tasks: {summary['order_driven_tasks']}")
    print(f"      • Total Orders: {summary['total_orders']}")
    print(f"      • Assignment Efficiency: {summary['integration_efficiency']:.1%}")
    
    print(f"\n   📋 Task Status Breakdown:")
    for status, count in summary['task_status_breakdown'].items():
        print(f"      • {status.title()}: {count}")
    
    print(f"\n   📦 Order Status Breakdown:")
    order_summary = summary['order_summary']
    for status, count in order_summary['status_breakdown'].items():
        print(f"      • {status.title()}: {count}")


def main():
    """Main demonstration function."""
    print("=" * 60)
    print("🎮 ORDER COLLECTION & ASSIGNMENT SYSTEM DEMO")
    print("=" * 60)
    print("This demo shows the implemented order system that:")
    print("• Collects orders from inventory graph deltas")
    print("• Maps orders to specific logistics tasks")
    print("• Weights priorities using fluid dynamics + order urgency")
    print("• Provides actionable task recommendations")
    print()
    
    # Initialize the integrator
    integrator = TaskOrderIntegrator()
    
    # Create demo scenario
    graph = create_demo_inventory_graph()
    
    # Demonstrate order collection
    tasks, orders = demonstrate_order_collection(integrator, graph)
    
    # Demonstrate task assignment
    demonstrate_task_assignment(integrator, tasks)
    
    # Demonstrate priority calculation
    demonstrate_priority_calculation(integrator)
    
    # Simulate blocking effects
    simulate_blocking_and_urgency(integrator)
    
    # Demonstrate order lifecycle
    demonstrate_order_lifecycle(integrator)
    
    # Show final summary
    show_integration_summary(integrator)
    
    print("\n" + "=" * 60)
    print("✅ DEMONSTRATION COMPLETE")
    print("The order system successfully:")
    print("✓ Collected orders from inventory deltas")
    print("✓ Assigned orders to appropriate tasks")
    print("✓ Calculated priorities using fluid dynamics + order urgency")
    print("✓ Provided actionable task recommendations")
    print("=" * 60)


if __name__ == "__main__":
    main()