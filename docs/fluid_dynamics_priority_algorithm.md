# Fluid Dynamics Priority Algorithm

## Overview

The Fluid Dynamics Priority Algorithm is a task prioritization system inspired by the physics of fluid dynamics and water pressure behind a dam. The algorithm calculates task priorities based on the concept that blocked upstream tasks create "pressure" that builds up over time, similar to how water builds pressure behind a dam.

## Core Concept

Just as water builds pressure behind a dam:
- **Blocked tasks** act like dams, preventing flow
- **Downstream tasks** experience increased "pressure" from blocked dependencies  
- **Time** increases the pressure as blockages persist
- **Multiple blockages** compound the effect like multiple dams in series
- **Priority weight** represents the "density" of the blocked resources

## Algorithm Components

### 1. Task Representation

Tasks are represented by the `Task` class with the following key properties:

- **task_id**: Unique identifier
- **status**: Current state (pending, blocked, in_progress, completed, failed)
- **base_priority**: Base weight from priority table (default 1.0)
- **blocked_since**: Timestamp when task became blocked
- **upstream_dependencies**: Set of task IDs this task depends on
- **downstream_dependents**: Set of task IDs that depend on this task

### 2. Priority Calculation Formula

```
Priority = (Total_Blocked_Weight × Time_Multiplier) + Base_Priority
```

Where:
- **Total_Blocked_Weight**: Sum of base priorities of all blocked upstream tasks
- **Time_Multiplier**: Exponential function based on blockage duration
- **Base_Priority**: Task's own base priority weight

### 3. Time Pressure Multiplier

The time pressure multiplier simulates increasing urgency over time:

```
Time_Multiplier = min(1 + (e^(hours × factor) - 1), max_multiplier)
```

Default parameters:
- **time_pressure_factor**: 0.1 (moderate pressure buildup)
- **max_time_multiplier**: 5.0 (caps exponential growth)

Example time progression:
- 0 hours: 1.00× multiplier
- 1 hour: 1.11× multiplier  
- 4 hours: 1.49× multiplier
- 8 hours: 2.23× multiplier
- 12 hours: 3.32× multiplier
- 24+ hours: 5.00× multiplier (capped)

## Usage Examples

### Basic Usage

```python
from services.tasks import Task, TaskStatus, FluidDynamicsPriorityCalculator

# Create calculator
calc = FluidDynamicsPriorityCalculator()

# Create tasks
blocked_task = Task("supply_1", "Material Supply", "supply", base_priority=2.0)
blocked_task.mark_blocked()

dependent_task = Task("production_1", "Rifle Production", "production", base_priority=3.0)
dependent_task.upstream_dependencies.add("supply_1")

# Add tasks to calculator
calc.add_task(blocked_task)
calc.add_task(dependent_task)

# Calculate priority
priority, details = calc.calculate_fluid_pressure("production_1")
print(f"Priority: {priority:.2f}")  # Output: Priority: 5.00 (2.0 + 3.0)

# Get rankings
rankings = calc.get_priority_rankings()
for task_id, priority, details in rankings:
    print(f"{task_id}: {priority:.2f}")
```

### Integration with Existing Graphs

```python
from services.tasks import GraphTaskIntegrator
import networkx as nx

# Create production graph  
prod_graph = nx.DiGraph()
prod_graph.add_node("iron", node=IronProductionNode())
prod_graph.add_node("steel", node=SteelProductionNode())
prod_graph.add_edge("iron", "steel")

# Integrate with priority system
integrator = GraphTaskIntegrator()
tasks = integrator.create_tasks_from_production_graph(prod_graph)

# Mark blockages
integrator.mark_production_blocked("iron", "Resource shortage")

# Get priority recommendations
recommendations = integrator.get_priority_recommendations(5)
for node_id, task_name, priority, details in recommendations:
    print(f"{node_id}: {priority:.2f} - {details['blocked_count']} blocked upstream")

# Generate report
report = integrator.generate_priority_report()
print(report)
```

## Key Features

### 1. Upstream Dependency Traversal
- Recursively finds all blocked tasks that prevent a given task from proceeding
- Handles complex dependency chains and graphs
- Cycle detection prevents infinite loops

### 2. Aggregated Weight Calculation
- Sums priority weights of all blocked upstream tasks
- Represents the "volume" of blocked resources
- Higher weights indicate more critical blockages

### 3. Time-Based Pressure Buildup
- Exponential time multiplier simulates increasing urgency
- Longer blockages automatically get higher priority
- Configurable growth rate and maximum multiplier

### 4. Detailed Analysis
- Provides breakdown of priority calculation components
- Shows which upstream tasks are blocked and for how long
- Includes calculation formula for transparency

### 5. Graph Integration
- Seamlessly integrates with existing NetworkX production graphs
- Converts inventory graphs to supply chain tasks
- Provides production/supply recommendations based on fluid dynamics

## Configuration Options

The `FluidDynamicsPriorityCalculator` accepts several configuration parameters:

```python
calc = FluidDynamicsPriorityCalculator(
    time_pressure_factor=0.1,    # How quickly pressure builds (per hour)
    max_time_multiplier=5.0,     # Maximum time-based multiplier
    base_priority_weight=1.0     # Default priority for tasks without specific weights
)
```

### Tuning Guidelines

- **Faster pressure buildup**: Increase `time_pressure_factor` (0.2-0.5)
- **Slower pressure buildup**: Decrease `time_pressure_factor` (0.05-0.1)  
- **Higher maximum urgency**: Increase `max_time_multiplier` (10.0+)
- **More conservative**: Decrease `max_time_multiplier` (2.0-3.0)

## Real-World Applications

### 1. Supply Chain Management
- Prioritize supply deliveries based on downstream impact
- Identify critical bottlenecks in logistics networks
- Balance resource allocation across multiple fronts

### 2. Production Planning
- Sequence production tasks to minimize overall delays
- Focus on unblocking high-impact dependencies first
- Account for facility downtime and resource shortages

### 3. Resource Allocation
- Direct limited resources to highest-pressure situations
- Consider both immediate needs and downstream consequences
- Optimize for overall system throughput

## Integration Points

The algorithm integrates with existing systems through:

### Production Graphs (`services.production_calculator.production_graph`)
- Converts production nodes to tasks
- Maps recipe dependencies to task dependencies
- Applies category-based priority weights

### Inventory Graphs (`services.inventory.inventory_graph`)
- Converts inventory nodes to supply tasks
- Uses inventory status and demand to set priorities
- Maps supply chain edges to task dependencies

### Task Layer (`services.task`)
- Provides the foundation task representation
- Manages task state and dependency relationships
- Integrates with the existing services architecture

## Testing

The algorithm includes comprehensive test coverage:

- **Unit tests**: 15 tests covering core functionality
- **Integration tests**: 8 tests for graph integration
- **Edge cases**: Circular dependencies, mixed states, time effects
- **Performance**: Efficient graph traversal algorithms

Run tests with:
```bash
python -m pytest tests/test_fluid_priority.py tests/test_graph_integration.py -v
```

## Performance Characteristics

- **Time Complexity**: O(V + E) for priority calculation (graph traversal)
- **Space Complexity**: O(V) for task storage and mappings
- **Scalability**: Handles hundreds of tasks with minimal overhead
- **Real-time**: Suitable for live priority updates and monitoring

## Future Enhancements

Potential areas for expansion:

1. **Machine Learning Integration**: Learn optimal priority weights from historical data
2. **Multi-Factor Scoring**: Include additional factors like resource cost, team availability
3. **Dynamic Reconfiguration**: Adjust algorithm parameters based on system conditions  
4. **Distributed Calculation**: Scale to larger task graphs across multiple systems
5. **Visualization**: Generate priority heatmaps and flow diagrams

## Conclusion

The Fluid Dynamics Priority Algorithm provides an intuitive and effective way to prioritize tasks in complex logistics systems. By modeling blocked dependencies as dams that create pressure, the algorithm helps identify which bottlenecks to address first for maximum system-wide impact.

The algorithm's strength lies in its ability to:
- Account for downstream consequences of blockages
- Automatically increase urgency over time
- Provide transparent priority calculations
- Integrate seamlessly with existing graph structures
- Scale to complex real-world scenarios

This makes it particularly well-suited for the dynamic, interconnected supply chains found in systems like Foxhole logistics management.