"""
Tests for the order system and task-order integration.
"""
import pytest
from datetime import datetime, timedelta
from services.inventory.order import Order, OrderManager, OrderType, OrderStatus
from services.inventory.inventory_graph import InventoryGraph, InventoryNode
from services.tasks import Task, TaskStatus, FluidDynamicsPriorityCalculator, TaskOrderIntegrator


class TestOrder:
    """Test the Order class functionality."""
    
    def test_order_creation(self):
        """Test basic order creation."""
        order = Order(
            order_id="test_order_1",
            order_type=OrderType.SUPPLY,
            item_type="rifle",
            quantity=50,
            source_node_id="depot_1",
            urgency=2.5
        )
        
        assert order.order_id == "test_order_1"
        assert order.order_type == OrderType.SUPPLY
        assert order.item_type == "rifle"
        assert order.quantity == 50
        assert order.source_node_id == "depot_1"
        assert order.status == OrderStatus.PENDING
        assert order.urgency == 2.5
        assert order.assigned_task_id is None
    
    def test_urgency_calculation_from_delta(self):
        """Test urgency calculation based on inventory deficit."""
        order = Order(
            order_id="test_order_1",
            order_type=OrderType.SUPPLY,
            item_type="rifle",
            quantity=50,
            source_node_id="depot_1"
        )
        
        # Test normal shortage
        urgency = order.calculate_urgency_from_delta(current_inventory=20, delta=-30)
        assert urgency > 1.0  # Should be elevated
        
        # Test critical shortage (inventory near zero)
        critical_urgency = order.calculate_urgency_from_delta(current_inventory=5, delta=-50)
        assert critical_urgency > urgency  # Should be higher
        
        # Test no shortage
        no_urgency = order.calculate_urgency_from_delta(current_inventory=100, delta=10)
        assert no_urgency == 1.0  # Should be normal
    
    def test_time_urgency_multiplier(self):
        """Test time-based urgency increase."""
        order = Order(
            order_id="test_order_1",
            order_type=OrderType.SUPPLY,
            item_type="rifle",
            quantity=50,
            source_node_id="depot_1"
        )
        
        # Simulate aged order
        order.created_at = datetime.utcnow() - timedelta(hours=12)
        
        multiplier = order.get_time_urgency_multiplier()
        assert multiplier > 1.0  # Should increase with age
        assert multiplier <= 2.0  # Should be capped
    
    def test_order_status_transitions(self):
        """Test order status changes."""
        order = Order(
            order_id="test_order_1",
            order_type=OrderType.SUPPLY,
            item_type="rifle",
            quantity=50,
            source_node_id="depot_1"
        )
        
        # Test assignment
        order.assign_to_task("task_123")
        assert order.status == OrderStatus.ASSIGNED
        assert order.assigned_task_id == "task_123"
        
        # Test progress
        order.mark_in_progress()
        assert order.status == OrderStatus.IN_PROGRESS
        
        # Test completion
        order.mark_completed()
        assert order.status == OrderStatus.COMPLETED
        
        # Test cancellation
        order2 = Order("test_order_2", OrderType.PRODUCTION, "ammo", 100, "factory_1")
        order2.mark_cancelled("Test cancellation")
        assert order2.status == OrderStatus.CANCELLED
        assert order2.metadata["cancellation_reason"] == "Test cancellation"


class TestOrderManager:
    """Test the OrderManager functionality."""
    
    def test_order_manager_initialization(self):
        """Test basic order manager creation."""
        manager = OrderManager()
        assert len(manager.orders) == 0
        assert manager.next_order_id == 1
    
    def test_order_id_generation(self):
        """Test unique order ID generation."""
        manager = OrderManager()
        
        id1 = manager.generate_order_id()
        id2 = manager.generate_order_id()
        
        assert id1 == "order_000001"
        assert id2 == "order_000002"
        assert id1 != id2
    
    def test_collect_orders_from_inventory_graph(self):
        """Test collecting orders from inventory deficits."""
        manager = OrderManager()
        
        # Create inventory graph with deficits
        graph = InventoryGraph()
        
        # Depot with rifle shortage
        depot = InventoryNode("depot_1", "Front Depot")
        depot.inventory = {"rifle": 10}
        depot.delta = {"rifle": -40}  # Need 40 more rifles
        depot.status = "critical"
        graph.add_node(depot)
        
        # Factory with ammo shortage
        factory = InventoryNode("factory_1", "Munitions Factory")
        factory.inventory = {"ammo": 100}
        factory.delta = {"ammo": -200}  # Need 200 more ammo
        factory.status = "low"
        graph.add_node(factory)
        
        # Collect orders
        orders = manager.collect_orders_from_inventory_graph(graph)
        
        assert len(orders) == 2
        
        # Check rifle order
        rifle_order = next(order for order in orders if order.item_type == "rifle")
        assert rifle_order.order_type == OrderType.SUPPLY
        assert rifle_order.quantity == 40
        assert rifle_order.source_node_id == "depot_1"
        assert rifle_order.urgency > 1.0  # Should be elevated due to shortage
        
        # Check ammo order
        ammo_order = next(order for order in orders if order.item_type == "ammo")
        assert ammo_order.quantity == 200
        assert ammo_order.source_node_id == "factory_1"
    
    def test_order_retrieval_methods(self):
        """Test various order retrieval methods."""
        manager = OrderManager()
        
        # Create some test orders
        order1 = Order("order_001", OrderType.SUPPLY, "rifle", 50, "depot_1")
        order2 = Order("order_002", OrderType.PRODUCTION, "ammo", 100, "factory_1")
        order3 = Order("order_003", OrderType.SUPPLY, "rifle", 25, "depot_2")
        
        manager.orders = {
            "order_001": order1,
            "order_002": order2,
            "order_003": order3
        }
        
        # Test get by type
        supply_orders = manager.get_orders_by_type(OrderType.SUPPLY)
        assert len(supply_orders) == 2
        
        production_orders = manager.get_orders_by_type(OrderType.PRODUCTION)
        assert len(production_orders) == 1
        
        # Test get by item
        rifle_orders = manager.get_orders_by_item("rifle")
        assert len(rifle_orders) == 2
        
        # Test get by node
        depot1_orders = manager.get_orders_by_node("depot_1")
        assert len(depot1_orders) == 1
        assert depot1_orders[0].order_id == "order_001"
        
        # Test get pending orders
        pending_orders = manager.get_pending_orders()
        assert len(pending_orders) == 3  # All are pending
    
    def test_order_summary(self):
        """Test order summary generation."""
        manager = OrderManager()
        
        # Create orders with different statuses
        order1 = Order("order_001", OrderType.SUPPLY, "rifle", 50, "depot_1")
        order2 = Order("order_002", OrderType.PRODUCTION, "ammo", 100, "factory_1")
        order2.mark_completed()
        
        manager.orders = {"order_001": order1, "order_002": order2}
        
        summary = manager.get_order_summary()
        
        assert summary["total_orders"] == 2
        assert summary["status_breakdown"]["pending"] == 1
        assert summary["status_breakdown"]["completed"] == 1
        assert summary["type_breakdown"]["supply"] == 1
        assert summary["type_breakdown"]["production"] == 1
        assert summary["pending_orders"] == 1


class TestTaskOrderIntegrator:
    """Test the TaskOrderIntegrator functionality."""
    
    def test_integrator_initialization(self):
        """Test basic integrator initialization."""
        integrator = TaskOrderIntegrator()
        
        assert integrator.priority_calc is not None
        assert integrator.order_manager is not None
        assert len(integrator.order_to_task_map) == 0
        assert len(integrator.task_to_orders_map) == 0
    
    def test_task_creation_from_order(self):
        """Test creating tasks from orders."""
        integrator = TaskOrderIntegrator()
        
        # Create test order
        order = Order(
            order_id="order_001",
            order_type=OrderType.SUPPLY,
            item_type="rifle",
            quantity=50,
            source_node_id="depot_1",
            urgency=3.0
        )
        order.metadata["source_location"] = "Front Depot"
        
        # Create task from order
        task = integrator._create_task_from_order(order)
        
        assert task.task_type == "supply"
        assert "rifle" in task.name
        assert "Front Depot" in task.name
        assert task.base_priority > 1.0  # Should be elevated due to order urgency
        assert task.metadata["source_node_id"] == "depot_1"
        assert task.metadata["order_driven"] is True
    
    def test_order_assignment_to_task(self):
        """Test assigning orders to tasks."""
        integrator = TaskOrderIntegrator()
        
        # Create test order
        order = Order("order_001", OrderType.SUPPLY, "rifle", 50, "depot_1")
        integrator.order_manager.orders["order_001"] = order
        
        # Assign order to task
        task = integrator._assign_order_to_task(order)
        
        assert task is not None
        assert order.status == OrderStatus.ASSIGNED
        assert order.assigned_task_id == task.task_id
        assert "order_001" in task.associated_orders
        assert integrator.order_to_task_map["order_001"] == task.task_id
    
    def test_priority_calculation_with_orders(self):
        """Test priority calculation including order urgency."""
        integrator = TaskOrderIntegrator()
        
        # Create task
        task = Task(
            task_id="task_001",
            name="Supply Rifles",
            task_type="supply",
            base_priority=2.0
        )
        integrator.priority_calc.add_task(task)
        
        # Create urgent order
        order = Order(
            order_id="order_001",
            order_type=OrderType.SUPPLY,
            item_type="rifle",
            quantity=50,
            source_node_id="depot_1",
            urgency=5.0
        )
        integrator.order_manager.orders["order_001"] = order
        
        # Link order to task
        integrator._link_order_to_task(order, task)
        
        # Calculate priority with orders
        priority, details = integrator.get_task_priority_with_orders("task_001")
        
        # Priority should be higher due to order urgency
        assert priority > task.base_priority
        assert details["order_urgency_bonus"] > 0
        assert len(details["associated_orders"]) == 1
        assert details["associated_orders"][0]["order_id"] == "order_001"
    
    def test_inventory_graph_processing(self):
        """Test end-to-end processing of inventory graph."""
        integrator = TaskOrderIntegrator()
        
        # Create inventory graph with deficits
        graph = InventoryGraph()
        
        depot = InventoryNode("depot_1", "Front Depot")
        depot.inventory = {"rifle": 5}
        depot.delta = {"rifle": -45}  # Critical shortage
        depot.status = "critical"
        graph.add_node(depot)
        
        # Process the graph
        tasks = integrator.process_inventory_graph_orders(graph)
        
        assert len(tasks) > 0
        
        # Check that orders were created (they will be assigned, not pending)
        all_orders = list(integrator.order_manager.orders.values())
        assert len(all_orders) == 1
        
        rifle_order = all_orders[0]
        assert rifle_order.item_type == "rifle"
        assert rifle_order.quantity == 45
        assert rifle_order.urgency > 1.0  # Should be urgent due to critical shortage
        
        # Check that task was created and linked
        task = tasks[0]
        assert task.has_orders()
        assert rifle_order.order_id in task.associated_orders
        assert rifle_order.status == OrderStatus.ASSIGNED
    
    def test_order_completion(self):
        """Test completing orders and updating tasks."""
        integrator = TaskOrderIntegrator()
        
        # Create and assign order
        order = Order("order_001", OrderType.SUPPLY, "rifle", 50, "depot_1")
        integrator.order_manager.orders["order_001"] = order
        
        task = integrator._assign_order_to_task(order)
        assert task.has_orders()
        
        # Complete the order
        result = integrator.complete_order("order_001")
        
        assert result is True
        assert order.status == OrderStatus.COMPLETED
        assert not task.has_orders()  # Order should be removed from task
        assert task.status == TaskStatus.COMPLETED  # Task should be completed too
    
    def test_multiple_orders_per_task(self):
        """Test handling multiple orders for the same task."""
        integrator = TaskOrderIntegrator()
        
        # Create multiple compatible orders
        order1 = Order("order_001", OrderType.SUPPLY, "rifle", 50, "depot_1")
        order2 = Order("order_002", OrderType.SUPPLY, "ammo", 100, "depot_1")
        
        integrator.order_manager.orders.update({
            "order_001": order1,
            "order_002": order2
        })
        
        # Assign orders
        task1 = integrator._assign_order_to_task(order1)
        task2 = integrator._assign_order_to_task(order2)
        
        # Should create compatible tasks that might be the same or different
        # depending on compatibility logic
        assert task1 is not None
        assert task2 is not None
        
        # Check that orders are properly assigned
        assert order1.status == OrderStatus.ASSIGNED
        assert order2.status == OrderStatus.ASSIGNED
    
    def test_integration_summary(self):
        """Test integration summary generation."""
        integrator = TaskOrderIntegrator()
        
        # Create some test data
        order = Order("order_001", OrderType.SUPPLY, "rifle", 50, "depot_1")
        integrator.order_manager.orders["order_001"] = order
        task = integrator._assign_order_to_task(order)
        
        summary = integrator.get_integration_summary()
        
        assert summary["total_tasks"] == 1
        assert summary["order_driven_tasks"] == 1
        assert summary["total_orders"] == 1
        assert summary["assigned_orders"] == 1
        assert summary["unassigned_orders"] == 0
        assert summary["integration_efficiency"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__])