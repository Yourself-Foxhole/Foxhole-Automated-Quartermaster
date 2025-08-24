"""
Task-Order Integration layer.

This module provides the bridge between the order collection system and the task priority system.
It handles order-to-task assignment, task creation from orders, and integration with the
fluid dynamics priority calculator.
"""
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime

from .task import Task, TaskStatus
from .fluid_priority import FluidDynamicsPriorityCalculator
from ..inventory.order import Order, OrderManager, OrderType, OrderStatus


class TaskOrderIntegrator:
    """
    Integrates orders with the task system to create order-driven task prioritization.
    
    This class manages the lifecycle of tasks created from orders and ensures
    that task priorities reflect both fluid dynamics and order urgency.
    """
    
    def __init__(self, priority_calculator: Optional[FluidDynamicsPriorityCalculator] = None,
                 order_manager: Optional[OrderManager] = None):
        """
        Initialize the integrator.
        
        Args:
            priority_calculator: FluidDynamicsPriorityCalculator instance
            order_manager: OrderManager instance for order tracking
        """
        self.priority_calc = priority_calculator or FluidDynamicsPriorityCalculator()
        self.order_manager = order_manager or OrderManager()
        self.order_to_task_map: Dict[str, str] = {}  # Maps order ID to task ID
        self.task_to_orders_map: Dict[str, Set[str]] = {}  # Maps task ID to order IDs
        self.next_task_id = 1
    
    def generate_task_id(self) -> str:
        """Generate a unique task ID."""
        task_id = f"task_{self.next_task_id:06d}"
        self.next_task_id += 1
        return task_id
    
    def process_inventory_graph_orders(self, inventory_graph) -> List[Task]:
        """
        Process an inventory graph to collect orders and create/update tasks.
        
        Args:
            inventory_graph: InventoryGraph to process for orders
            
        Returns:
            List of tasks that were created or updated
        """
        # Collect new orders from the inventory graph
        new_orders = self.order_manager.collect_orders_from_inventory_graph(inventory_graph)
        
        # Process each new order and assign to tasks
        updated_tasks = []
        for order in new_orders:
            task = self._assign_order_to_task(order)
            if task:
                updated_tasks.append(task)
        
        return updated_tasks
    
    def _assign_order_to_task(self, order: Order) -> Optional[Task]:
        """
        Assign an order to an appropriate task, creating a new task if necessary.
        
        Args:
            order: Order to assign to a task
            
        Returns:
            Task that the order was assigned to, or None if assignment failed
        """
        # Look for existing compatible task
        compatible_task = self._find_compatible_task(order)
        
        if compatible_task:
            # Assign order to existing task
            self._link_order_to_task(order, compatible_task)
            return compatible_task
        else:
            # Create new task for this order
            new_task = self._create_task_from_order(order)
            if new_task:
                self.priority_calc.add_task(new_task)
                self._link_order_to_task(order, new_task)
                return new_task
        
        return None
    
    def _find_compatible_task(self, order: Order) -> Optional[Task]:
        """
        Find an existing task that can handle this order.
        
        Args:
            order: Order to find a compatible task for
            
        Returns:
            Compatible Task or None if no compatible task exists
        """
        # Look for tasks of the same type for the same node
        for task_id, task in self.priority_calc.task_graph.items():
            # Check if task type matches order type
            if self._task_type_matches_order(task, order):
                # Check if task is for the same location/node
                if self._task_handles_same_location(task, order):
                    # Check if task isn't already overloaded
                    if task.get_order_count() < 5:  # Max 5 orders per task
                        return task
        
        return None
    
    def _task_type_matches_order(self, task: Task, order: Order) -> bool:
        """Check if a task type is compatible with an order type."""
        type_mapping = {
            OrderType.SUPPLY: ["supply", "transport"],
            OrderType.PRODUCTION: ["production"],
            OrderType.TRANSPORT: ["transport", "supply"],
            OrderType.REFILL: ["supply", "refill"]
        }
        
        compatible_types = type_mapping.get(order.order_type, [])
        return task.task_type in compatible_types
    
    def _task_handles_same_location(self, task: Task, order: Order) -> bool:
        """Check if a task handles the same location as an order."""
        # Check if task metadata contains the same source node
        task_node = task.metadata.get("source_node_id")
        return task_node == order.source_node_id
    
    def _create_task_from_order(self, order: Order) -> Task:
        """
        Create a new task to handle an order.
        
        Args:
            order: Order to create a task for
            
        Returns:
            New Task object
        """
        task_id = self.generate_task_id()
        
        # Determine task type from order type
        task_type_mapping = {
            OrderType.SUPPLY: "supply",
            OrderType.PRODUCTION: "production",
            OrderType.TRANSPORT: "transport",
            OrderType.REFILL: "supply"
        }
        task_type = task_type_mapping.get(order.order_type, "supply")
        
        # Create task name based on order
        task_name = f"{task_type.title()} {order.item_type} for {order.metadata.get('source_location', order.source_node_id)}"
        
        # Determine base priority from order urgency
        base_priority = max(1.0, order.urgency * 0.5)  # Scale order urgency to task priority
        
        # Create the task
        task = Task(
            task_id=task_id,
            name=task_name,
            task_type=task_type,
            base_priority=base_priority
        )
        
        # Add order-specific metadata
        task.metadata.update({
            "source_node_id": order.source_node_id,
            "primary_item_type": order.item_type,
            "created_from_order": order.order_id,
            "order_driven": True
        })
        
        return task
    
    def _link_order_to_task(self, order: Order, task: Task) -> None:
        """
        Create bidirectional link between order and task.
        
        Args:
            order: Order to link
            task: Task to link to
        """
        # Update order
        order.assign_to_task(task.task_id)
        
        # Update task
        task.add_order(order.order_id)
        
        # Update mappings
        self.order_to_task_map[order.order_id] = task.task_id
        if task.task_id not in self.task_to_orders_map:
            self.task_to_orders_map[task.task_id] = set()
        self.task_to_orders_map[task.task_id].add(order.order_id)
    
    def get_task_priority_with_orders(self, task_id: str) -> Tuple[float, Dict[str, Any]]:
        """
        Get task priority including order urgency calculations.
        
        Args:
            task_id: ID of task to calculate priority for
            
        Returns:
            Tuple of (priority_score, calculation_details)
        """
        return self.priority_calc.calculate_fluid_pressure(task_id, self.order_manager)
    
    def get_priority_rankings_with_orders(self, top_n: Optional[int] = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Get priority rankings including order urgency.
        
        Args:
            top_n: Optional limit on number of results
            
        Returns:
            List of (task_id, priority_score, details) sorted by priority
        """
        rankings = self.priority_calc.get_priority_rankings(order_manager=self.order_manager)
        
        if top_n:
            rankings = rankings[:top_n]
        
        return rankings
    
    def complete_order(self, order_id: str) -> bool:
        """
        Mark an order as completed and update associated task.
        
        Args:
            order_id: ID of order to complete
            
        Returns:
            True if order was found and completed, False otherwise
        """
        order = self.order_manager.get_order(order_id)
        if not order:
            return False
        
        # Mark order as completed
        order.mark_completed()
        
        # Update task
        task_id = self.order_to_task_map.get(order_id)
        if task_id:
            task = self.priority_calc.get_task(task_id)
            if task:
                task.remove_order(order_id)
                
                # If task has no more orders, consider completing it
                if not task.has_orders():
                    task.status = TaskStatus.COMPLETED
        
        return True
    
    def cancel_order(self, order_id: str, reason: str = "") -> bool:
        """
        Cancel an order and update associated task.
        
        Args:
            order_id: ID of order to cancel
            reason: Reason for cancellation
            
        Returns:
            True if order was found and cancelled, False otherwise
        """
        order = self.order_manager.get_order(order_id)
        if not order:
            return False
        
        # Mark order as cancelled
        order.mark_cancelled(reason)
        
        # Update task
        task_id = self.order_to_task_map.get(order_id)
        if task_id:
            task = self.priority_calc.get_task(task_id)
            if task:
                task.remove_order(order_id)
                
                # If task has no more orders, consider cancelling it
                if not task.has_orders():
                    task.status = TaskStatus.CANCELLED
                    task.metadata["cancellation_reason"] = f"All orders cancelled: {reason}"
        
        return True
    
    def get_integration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current task-order integration state.
        
        Returns:
            Dictionary with integration statistics
        """
        total_tasks = len(self.priority_calc.task_graph)
        order_driven_tasks = sum(1 for task in self.priority_calc.task_graph.values() 
                                if task.metadata.get("order_driven", False))
        total_orders = len(self.order_manager.orders)
        assigned_orders = len(self.order_to_task_map)
        
        # Get status breakdowns
        task_status_counts = {}
        for task in self.priority_calc.task_graph.values():
            status = task.status.value
            task_status_counts[status] = task_status_counts.get(status, 0) + 1
        
        order_summary = self.order_manager.get_order_summary()
        
        return {
            "total_tasks": total_tasks,
            "order_driven_tasks": order_driven_tasks,
            "total_orders": total_orders,
            "assigned_orders": assigned_orders,
            "unassigned_orders": total_orders - assigned_orders,
            "task_status_breakdown": task_status_counts,
            "order_summary": order_summary,
            "integration_efficiency": assigned_orders / max(1, total_orders)
        }