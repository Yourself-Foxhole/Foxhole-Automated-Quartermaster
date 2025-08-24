# Transportation Cost Algorithm Documentation

## Overview

The transportation cost algorithm models the movement of goods across the Foxhole logistics network using an inventory graph. Each edge in the graph represents a possible route between two nodes (locations), and can be assigned a transportation time. This time is a key factor in calculating the cost and efficiency of moving items.

## Transport Time Attribute

### Basic Usage

The `InventoryGraph` supports an optional `transport_time` attribute on edges that represents the time in hours to transport items via that route:

```python
from services.inventory.inventory_graph import InventoryGraph, InventoryNode

# Create graph and nodes
graph = InventoryGraph()
depot = InventoryNode("depot", "Supply Depot")
frontline = InventoryNode("frontline", "Frontline Base")
graph.add_node(depot)
graph.add_node(frontline)

# Add edge with transport time (3.0 hours)
graph.add_edge("depot", "frontline", 
               allowed_items=["rifle"], 
               transport_time=3.0)

# Add edge without transport time (defaults to None)
graph.add_edge("frontline", "depot", 
               allowed_items=["ammo"])
```

### Edge Methods

```python
# Get the edge
edge = graph.edges[0]

# Check if edge has transport time configured
if edge.has_transport_time():
    time = edge.get_transport_time()
    print(f"Transport time: {time} hours")

# Set or update transport time
edge.set_transport_time(2.5)

# Clear transport time
edge.set_transport_time(None)
```

### Integration with Task Generation

When the `TaskGenerator` creates transportation tasks, it automatically includes the `transport_time` in the task's priority signals when available:

```python
from services.tasks.task_layer import TaskGenerator

# Set up nodes with inventory and demand
source.inventory = {"rifle": 100}
target.delta = {"rifle": 50}

# Create tasks
task_gen = TaskGenerator([source, target])
tasks = task_gen.get_actionable_tasks()

# Transportation tasks will include transport_time in priority signals
for task in tasks:
    if task.task_type == "transportation" and "transport_time" in task.priority.signals:
        print(f"Transport time: {task.priority.signals['transport_time']} hours")
```

### Priority Calculation

Transport time is integrated into the priority system as a signal with a default weight of `-0.3`. This negative weight means shorter transport times result in higher priority:

```python
from services.tasks.task_layer import Priority

signals = {
    "delta": 20.0,          # Items needed
    "inventory": 10.0,      # Available inventory  
    "status": 1.0,          # Node status (low)
    "transport_time": 2.5   # Transport time in hours
}

priority = Priority(signals)
# Score calculation includes: ... + (-0.3 * 2.5) = ... - 0.75
```

### Backward Compatibility

- Existing code that doesn't use `transport_time` continues to work unchanged
- TaskGenerator gracefully handles edges without transport time
- Priority calculations work normally when `transport_time` signal is absent
- Default behavior is preserved when transport time is not configured

## Edge Times and LogiWaze Integration

- **Edge Time Input:**
  - For each edge, users are prompted to provide time estimates from LogiWaze.
  - Two times are required:
    - **Regular Vehicle Time:** Standard trucks and vehicles.
    - **Flatbed Time:** For flatbed vehicles, which may have different travel times.
- **Other Methods:**
  - Users can also post estimates for alternative transportation methods (e.g., water logi).
  - For each method, users specify:
    - Vehicle type
    - Storage capacity
    - Capacity for items, crates, and shippables
  - The system does not enforce a fixed list, allowing flexibility for user input.

## Storage Types in Foxhole

- **Inventory Stacks:**
  - Immediate access, limited size.
  - Can store item stacks or crates.
  - Stack size varies by item (from 1 up to 100 per stack; see database for specifics).
- **Stockpiles:**
  - Larger storage, but require assembly time.
  - Items must be in original condition to be stockpiled (attributes like fuel or used ammo are removed).

## Common Vehicle Templates

Below are templates for frequently used vehicle types. Users can customize these as needed:

### Flatbed Train
- 1 shippable per car
- Max train length: 15 cars (including locomotive)
- Users may customize train loadout

### Freighter
- 5 shippables
- 10 crates

### Flatbed (BMS Packmule)
- 1 shippable
- 1 inventory slot

### Base Truck (R-5 Hauler or Dunne Transport)
- 15 inventory slots

### Specialized Truck (Dunne Landrunner or variant)
- 14 inventory slots

## Usage Notes

- When specifying transportation options, users should provide as much detail as possible for accurate cost calculation.
- Storage capacities and stack sizes for items are available in the database and should be referenced for planning.
- The system is designed to be flexible, supporting custom vehicle types and transportation methods as needed.

## Suggested Classes & User Stories

### Class Suggestions
- **VehicleTemplate**: Represents a standard vehicle type (e.g., Flatbed Train, Freighter) with default capacities and attributes. Vehicles should always have a template type, which can be referenced or extended for custom vehicles.
- **CustomVehicle**: Allows users to define custom vehicles, specifying type, storage, and capacities. Users can override template defaults for specialized needs.
- **Route**: Represents a path between two nodes, with allowed vehicle types and transportation modes. Users can specify which vehicle types are permitted on each route.
- **TransportationMode**: Encapsulates a mode (road, rail, water, etc.), time estimates, and vehicle compatibility. Users can define custom modes and provide time estimates for each.
- **NetworkDecisionEngine**: Evaluates whether to transport or produce locally, factoring in times, surplus, knock-on effects, and fallback logic if transportation time is not provided.

### User Stories
- As a logistics planner, I want to select which vehicle types are allowed on a route so I can optimize for speed or capacity.
- As a user, I want to define custom transportation modes and times for a route, so I can model unique scenarios (e.g., water logi).
- As a network manager, I want the system to compare transportation time vs. local production time, so I can choose the most efficient option. If transportation time is not provided, the system should default to production-only logic.
- As a planner, I want the network to consider additional transit times (e.g., refinery replenishment) when calculating total delivery time, including knock-on effects for backfilling.
- As a user, I want surplus inventory to be considered in backfilling calculations, so time estimates are realistic and not overstated. If surplus exists, backfilling time should be fractional or omitted.
- As a user, I want the option to skip entering transportation times, so the system will automatically order everything for production and disable transport time features for those nodes/routes.

## Advanced Transportation Logic

- **Vehicle Templates & Customization:**
  - Each vehicle should have a template type, with default attributes and capacities.
  - Users can specify which vehicle types are allowed on a route, or define custom vehicles.
- **Custom Transportation Modes:**
  - Users may specify custom modes (e.g., water, air) and provide time estimates per route.
- **Production vs. Transportation Decision:**
  - The network should compare transportation time to local production time.
  - If transportation time is close to or exceeds production time, local production is preferred (if possible).
  - If transportation time is not provided for a node or route, the system should default to production-only logic and disable transport time features for those nodes/routes.
- **Knock-On Effects:**
  - When items require further processing (e.g., bmats at a frontline factory with no refinery), the network should factor in additional transit times for replenishment or backfill.
- **Backfilling & Surplus:**
  - If there is surplus inventory, backfilling time should be adjusted (not counted as full transit time, but as a fraction or not at all if unused).

## Optional Transportation Time & Fallback Logic

Transportation time is not required for all nodes or routes. If a user does not enter a transportation time, the system will:
- Default to production-only logic for those nodes/routes.
- Disable transportation time features for those nodes/routes.
- If needed automatically order everything for transportation or production, ignoring transport time calculations.

This ensures the system remains flexible and user-friendly, allowing users to focus on production when transportation data is unavailable or unnecessary.

## Implementation Notes

- These suggestions are intended for future development and can be referenced when expanding the transportation cost algorithm.
- User stories can guide feature development and testing.
- Class suggestions provide a foundation for structuring code and logic.

---

For further details on the algorithm or to contribute new vehicle templates, please refer to the implementation files or contact the maintainers.
