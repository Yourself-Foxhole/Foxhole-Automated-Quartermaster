"""
Demonstration of the Fluid Dynamics Priority Algorithm

This script shows how the priority system works with a realistic logistics scenario.
"""
import sys
import os
sys.path.append('/home/runner/work/Foxhole-Automated-Quartermaster/Foxhole-Automated-Quartermaster')

from datetime import datetime, timedelta, timezone
from services.tasks import Task, TaskStatus, FluidDynamicsPriorityCalculator


def create_logistics_scenario():
    """
    Create a realistic logistics scenario to demonstrate the fluid dynamics priority algorithm.
    
    Scenario: Supply chain for frontline operations
    - Raw materials extraction is blocked
    - Multiple production steps depend on raw materials
    - Transport tasks depend on production
    - Combat units are waiting for supplies
    """
    calc = FluidDynamicsPriorityCalculator(
        time_pressure_factor=0.05,  # Moderate time pressure buildup
        max_time_multiplier=3.0,    # Cap at 3x multiplier
        base_priority_weight=1.0
    )
    
    # Raw material extraction (BLOCKED - simulating resource shortage)
    salvage_extraction = Task(
        task_id="salvage_extract",
        name="Salvage Field Extraction",
        task_type="resource_extraction",
        base_priority=1.0
    )
    salvage_extraction.mark_blocked()
    # Simulate this has been blocked for 2 hours
    salvage_extraction.blocked_since = datetime.utcnow() - timedelta(hours=2)
    
    # Component production (depends on salvage)
    component_production = Task(
        task_id="component_prod",
        name="Basic Materials Production",
        task_type="production",
        base_priority=2.0
    )
    component_production.upstream_dependencies.add("salvage_extract")
    
    # Advanced production (depends on components)
    rifle_production = Task(
        task_id="blakerow_prod",
        name="Blakerow 871 Production",
        task_type="production",
        base_priority=4.0
    )
    rifle_production.upstream_dependencies.add("component_prod")
    
    ammo_production = Task(
        task_id="ammo_762_prod",
        name="7.62 mm Ammo Production", 
        task_type="production",
        base_priority=3.5
    )
    ammo_production.upstream_dependencies.add("component_prod")
    
    # Transport tasks (depend on production)
    rifle_transport = Task(
        task_id="blakerow_transport",
        name="Blakerow 871 Transport to Front",
        task_type="transport",
        base_priority=5.0
    )
    rifle_transport.upstream_dependencies.add("blakerow_prod")
    
    ammo_transport = Task(
        task_id="ammo_762_transport", 
        name="7.62 mm Ammo Transport to Front",
        task_type="transport",
        base_priority=6.0  # High priority - troops need ammo
    )
    ammo_transport.upstream_dependencies.add("ammo_762_prod")
    
    # Medical supplies (independent production, higher priority)
    medical_production = Task(
        task_id="bandages_prod",
        name="Bandages Production",
        task_type="production",
        base_priority=7.0
    )
    
    medical_transport = Task(
        task_id="bandages_transport",
        name="Bandages Transport to Front",
        task_type="transport", 
        base_priority=8.0  # Critical priority
    )
    medical_transport.upstream_dependencies.add("bandages_prod")
    
    # Artillery production (also blocked independently)
    artillery_production = Task(
        task_id="120mm_shell_prod",
        name="120 mm Shell Production",
        task_type="production",
        base_priority=4.5
    )
    artillery_production.mark_blocked()
    # This has been blocked for 4 hours
    artillery_production.blocked_since = datetime.now(timezone.utc) - timedelta(hours=4)
    
    artillery_transport = Task(
        task_id="120mm_pallet_transport",
        name="120 mm Pallet Transport to Front (120 shells each)",
        task_type="transport",
        base_priority=5.5
    )
    artillery_transport.upstream_dependencies.add("120mm_shell_prod")
    
    # Add all tasks to calculator
    tasks = [
        salvage_extraction, component_production, rifle_production, ammo_production,
        rifle_transport, ammo_transport, medical_production, medical_transport,
        artillery_production, artillery_transport
    ]
    
    for task in tasks:
        calc.add_task(task)
    
    return calc, tasks


def demonstrate_priority_algorithm():
    """Demonstrate the fluid dynamics priority algorithm with detailed analysis."""
    print("=" * 60)
    print("FLUID DYNAMICS PRIORITY ALGORITHM DEMONSTRATION")
    print("=" * 60)
    print("\nScenario: Foxhole Logistics Supply Chain")
    print("- Salvage extraction blocked for 2 hours (resource shortage)")
    print("- Artillery production blocked for 4 hours (facility damage)")
    print("- Multiple tasks depend on these blocked upstream tasks")
    print("- Priority calculated based on 'fluid pressure' from blocked tasks")
    
    calc, tasks = create_logistics_scenario()
    
    print("{:<20}".format("\nTask Analysis:"))
    print("-" * 60)
    
    # Get priority rankings
    rankings = calc.get_priority_rankings()
    
    print("{:<5} {:<20} {:<10} {:<15} {:<12}".format("Rank", "Task ID", "Priority", "Type", "Status"))
    print("-" * 60)
    
    for i, (task_id, priority, details) in enumerate(rankings):
        task = calc.get_task(task_id)
        print("{:<5} {:<20} {:<10.2f} {:<15} {:<12}".format(i+1, task_id, priority, task.task_type, task.status.value))
    
    print("\n" + "=" * 60)
    print("DETAILED PRIORITY ANALYSIS")
    print("=" * 60)
    
    # Show detailed analysis for top 5 priority tasks
    top_tasks = rankings[:5]
    
    for i, (task_id, priority, details) in enumerate(top_tasks):
        print("\n{}. ANALYSIS FOR: {}".format(i+1, calc.get_task(task_id).name))
        print("-" * 40)
        calc.print_priority_analysis(task_id)
    
    print("\n" + "=" * 60)
    print("KEY INSIGHTS")
    print("=" * 60)
    print("1. Blocked tasks create 'pressure' that propagates downstream")
    print("2. Longer blockage duration increases time pressure multiplier")
    print("3. Tasks with higher base priority + blocked dependencies get top priority")
    print("4. Artillery transport has very high priority due to 4-hour blockage")
    print("5. Medical supplies maintain high priority (independent production)")
    print("6. The algorithm helps identify critical bottlenecks to address first")


def demonstrate_time_pressure_effect():
    """Show how time pressure affects priorities over time."""
    print("\n" + "=" * 60)
    print("TIME PRESSURE EFFECT DEMONSTRATION")
    print("=" * 60)
    
    calc = FluidDynamicsPriorityCalculator(time_pressure_factor=0.1, max_time_multiplier=5.0)
    
    # Create a simple blocked task
    blocked_task = Task("critical_supply", "Critical Supply Production", "production", base_priority=3.0)
    blocked_task.mark_blocked()
    
    dependent_task = Task("front_delivery", "Frontline Delivery", "transport", base_priority=2.0)
    dependent_task.upstream_dependencies.add("critical_supply")
    
    calc.add_task(blocked_task)
    calc.add_task(dependent_task)
    
    print("\nPriority evolution over time:")
    print("{:<15} {:<18} {:<15}".format("Hours Blocked", "Time Multiplier", "Final Priority"))
    print("-" * 50)
    
    test_hours = [0, 1, 2, 4, 8, 12, 24, 48]
    
    for hours in test_hours:
        # Simulate blocked duration
        blocked_task.blocked_since = datetime.utcnow() - timedelta(hours=hours)
        
        priority, details = calc.calculate_fluid_pressure("front_delivery")
        time_mult = details["time_multiplier"]
        
        print("{:<15} {:<18} {:<15}".format(hours, round(time_mult, 3), round(priority, 2)))
    
    print("\nAs you can see, priority increases exponentially with blockage duration,")
    print("simulating increasing 'pressure' like water building behind a dam.")


if __name__ == "__main__":
    demonstrate_priority_algorithm()
    demonstrate_time_pressure_effect()