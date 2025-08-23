
"""Demonstration of the Fluid Dynamics Priority Algorithm.

This script shows how the priority system works with a realistic logistics scenario.
"""

from datetime import datetime, timedelta
from services.tasks import Task, FluidDynamicsPriorityCalculator

from datetime import datetime, timedelta
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
        task_id="rifle_prod",
        name="Blakerow 871",
        task_type="production",
        base_priority=4.0
    )
    rifle_production.upstream_dependencies.add("component_prod")
    
    ammo_production = Task(
        task_id="ammo_prod",
        name="120 mm Shell",
        task_type="production",
        base_priority=3.5
    )
    ammo_production.upstream_dependencies.add("component_prod")
    
    # Transport tasks (depend on production)
    rifle_transport = Task(
        task_id="rifle_transport",
        name="Blakerow 871 Transport to Front",
        task_type="transport",
        base_priority=5.0
    )
    rifle_transport.upstream_dependencies.add("rifle_prod")
    
    ammo_transport = Task(
        task_id="ammo_transport", 
        name="7.62mm Ammo Transport to Front",
        task_type="transport",
        base_priority=6.0  # High priority - troops need ammo
    )
    ammo_transport.upstream_dependencies.add("ammo_prod")
    
    # Medical supplies (independent production, higher priority)
    medical_production = Task(
        task_id="medical_prod",
        name="Medical Supplies Production",
        task_type="production",
        base_priority=7.0
    )
    
    medical_transport = Task(
        task_id="medical_transport",
        name="Medical Transport to Front",
        task_type="transport", 
        base_priority=8.0  # Critical priority
    )
    medical_transport.upstream_dependencies.add("medical_prod")
    
    # Artillery production (also blocked independently)
    artillery_production = Task(
        task_id="artillery_prod",
        name="Artillery Shell Production",
        task_type="production",
        base_priority=4.5
    )
    artillery_production.mark_blocked()
    # This has been blocked for 4 hours
    artillery_production.blocked_since = datetime.utcnow() - timedelta(hours=4)
    
    artillery_transport = Task(
        task_id="artillery_transport",
        name="Artillery Transport to Front",
        task_type="transport",
        base_priority=5.5
    )
    artillery_transport.upstream_dependencies.add("artillery_prod")
    
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
    
    print(f"\n{'Task Analysis:':<20}")
    print("-" * 60)
    
    # Get priority rankings
    rankings = calc.get_priority_rankings()
    
    print(f"{'Rank':<5} {'Task ID':<20} {'Priority':<10} {'Type':<15} {'Status':<12}")
    print("-" * 60)
    
    for i, (task_id, priority, details) in enumerate(rankings):
        task = calc.get_task(task_id)
        print(f"{i+1:<5} {task_id:<20} {priority:<10.2f} {task.task_type:<15} {task.status.value:<12}")
    
    print("\n" + "=" * 60)
    print("DETAILED PRIORITY ANALYSIS")
    print("=" * 60)
    
    # Show detailed analysis for top 5 priority tasks
    top_tasks = rankings[:5]
    
    for i, (task_id, priority, details) in enumerate(top_tasks):
        print(f"\n{i+1}. ANALYSIS FOR: {calc.get_task(task_id).name}")
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
    print(f"{'Hours Blocked':<15} {'Time Multiplier':<18} {'Final Priority':<15}")
    print("-" * 50)
    
    test_hours = [0, 1, 2, 4, 8, 12, 24, 48]
    
    for hours in test_hours:
        # Simulate blocked duration
        blocked_task.blocked_since = datetime.utcnow() - timedelta(hours=hours)
        
        priority, details = calc.calculate_fluid_pressure("front_delivery")
        time_mult = details["time_multiplier"]
        
        print(f"{hours:<15} {time_mult:<18.3f} {priority:<15.2f}")
    
    print("\nAs you can see, priority increases exponentially with blockage duration,")
    print("simulating increasing 'pressure' like water building behind a dam.")


if __name__ == "__main__":
    demonstrate_priority_algorithm()
    demonstrate_time_pressure_effect()