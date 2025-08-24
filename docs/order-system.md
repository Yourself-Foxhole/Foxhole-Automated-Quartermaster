# Order Collection & Assignment System

The Order Collection & Assignment System is a comprehensive logistics management solution that automatically detects inventory shortages and creates actionable tasks with priority weighting based on both fluid dynamics and order urgency.

## Overview

The system consists of three main components:

1. **Order Management**: Collects and manages orders from inventory graph deltas
2. **Task-Order Integration**: Maps orders to appropriate tasks and manages their lifecycle
3. **Enhanced Priority Calculation**: Extends the fluid dynamics algorithm with order urgency

## Key Components

### Order Class (`services/inventory/order.py`)

Represents an actionable logistics order with:
- **Order Types**: SUPPLY, PRODUCTION, TRANSPORT, REFILL
- **Status Tracking**: PENDING → ASSIGNED → IN_PROGRESS → COMPLETED/CANCELLED
- **Urgency Calculation**: Dynamic urgency based on shortage severity and time factors
- **Metadata**: Source location, inventory status, shortage quantities

```python
from services.inventory.order import Order, OrderType, OrderStatus

order = Order(
    order_id="order_001",
    order_type=OrderType.SUPPLY,
    item_type="rifle",
    quantity=50,
    source_node_id="depot_1",
    urgency=3.5  # Calculated based on shortage
)
```

### OrderManager

Manages the collection and lifecycle of orders:
- **Automatic Collection**: Scans inventory graph deltas for shortages
- **Smart Order Creation**: Determines appropriate order types based on context
- **Order Retrieval**: Various filtering and search methods
- **Lifecycle Management**: Complete order status tracking

```python
from services.inventory.order import OrderManager
from services.inventory.inventory_graph import InventoryGraph

manager = OrderManager()
# Collect orders from inventory shortages
orders = manager.collect_orders_from_inventory_graph(inventory_graph)
```

### TaskOrderIntegrator (`services/tasks/task_order_integration.py`)

Integrates orders with the task system:
- **Order-to-Task Assignment**: Maps orders to compatible tasks
- **Task Creation**: Creates new tasks when no compatible task exists
- **Priority Enhancement**: Includes order urgency in task priority calculations
- **Lifecycle Integration**: Manages order completion and task updates

```python
from services.tasks import TaskOrderIntegrator

integrator = TaskOrderIntegrator()
# Process inventory graph to create tasks from orders
tasks = integrator.process_inventory_graph_orders(inventory_graph)
# Get priority rankings with order urgency
rankings = integrator.get_priority_rankings_with_orders()
```

## Enhanced Priority Calculation

The fluid dynamics priority calculator now includes order urgency:

**Priority = (blocked_weight × time_multiplier) + base_priority + order_urgency_bonus**

Where:
- `blocked_weight`: Sum of priorities of blocked upstream tasks
- `time_multiplier`: Exponential increase based on how long tasks have been blocked
- `base_priority`: Task's base priority from configuration
- `order_urgency_bonus`: Sum of urgency from all associated orders

## Usage Examples

### Basic Order Collection

```python
from services.tasks import TaskOrderIntegrator
from services.inventory.inventory_graph import InventoryGraph, InventoryNode

# Create inventory graph with shortages
graph = InventoryGraph()
depot = InventoryNode("depot_1", "Front Depot")
depot.inventory = {"rifle": 5}
depot.delta = {"rifle": -45}  # Need 45 more rifles
depot.status = "critical"
graph.add_node(depot)

# Process orders and create tasks
integrator = TaskOrderIntegrator()
tasks = integrator.process_inventory_graph_orders(graph)

# Get priority recommendations
rankings = integrator.get_priority_rankings_with_orders(top_n=5)
for task_id, priority, details in rankings:
    print(f"Task: {task_id}, Priority: {priority:.2f}")
```

### Order Lifecycle Management

```python
# Complete an order
integrator.complete_order("order_001")

# Cancel an order
integrator.cancel_order("order_002", reason="Supply route compromised")

# Get system summary
summary = integrator.get_integration_summary()
print(f"Assignment efficiency: {summary['integration_efficiency']:.1%}")
```

## Testing

The system includes comprehensive test coverage:

```bash
# Run order system tests
python -m pytest tests/test_order_system.py -v

# Run all task-related tests
python -m pytest tests/test_fluid_priority.py tests/test_graph_integration.py tests/test_order_system.py -v
```

## Demonstration

Run the complete demonstration:

```bash
python demo_order_system.py
```

This shows:
- Order collection from inventory deficits
- Task creation and assignment
- Priority calculation with order urgency
- Fluid dynamics effects with task blocking
- Order lifecycle management

## Integration Points

### With Existing Task System
- Orders seamlessly integrate with existing `Task` objects
- `FluidDynamicsPriorityCalculator` enhanced to include order urgency
- `GraphTaskIntegrator` can work alongside the order system

### With Inventory System
- Orders automatically collected from `InventoryGraph` deltas
- Compatible with existing `InventoryNode` structure
- Maintains all existing inventory functionality

### Production Chain Integration
- Orders can trigger production tasks at facilities
- Supply orders can be created for resource extraction
- Transport orders can move items between locations

## Key Benefits

1. **Automated Logistics**: No manual order creation - system detects needs automatically
2. **Intelligent Prioritization**: Combines fluid dynamics with order urgency for optimal task ordering
3. **Complete Lifecycle**: Full order tracking from creation to completion
4. **Scalable**: Handles multiple orders per task and complex dependency chains
5. **Backward Compatible**: Existing functionality preserved and enhanced

The Order Collection & Assignment System provides a robust foundation for automated logistics management in the Foxhole Quartermaster application.