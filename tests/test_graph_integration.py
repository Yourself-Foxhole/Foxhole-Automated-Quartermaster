"""
Tests for the graph integration module.
"""
import pytest
import networkx as nx
from services.tasks import GraphTaskIntegrator, Task, TaskStatus
from services.inventory.inventory_graph import InventoryGraph, InventoryNode


class TestGraphTaskIntegrator:
    """Test the GraphTaskIntegrator functionality."""
    
    def test_integrator_initialization(self):
        """Test basic integrator initialization."""
        integrator = GraphTaskIntegrator()
        
        assert integrator.priority_calc is not None
        assert len(integrator.node_to_task_map) == 0
        assert len(integrator.task_to_node_map) == 0
    
    def test_production_graph_integration(self):
        """Test converting a production graph to tasks."""
        integrator = GraphTaskIntegrator()
        
        # Create simple production graph
        graph = nx.DiGraph()
        
        class MockNode:
            def __init__(self, name, category):
                self.name = name
                self.category = category
        
        graph.add_node("iron", node=MockNode("Iron Production", "resource"))
        graph.add_node("steel", node=MockNode("Steel Production", "refined"))
        graph.add_edge("iron", "steel")
        
        priority_map = {"iron": 1.0, "steel": 3.0}
        tasks = integrator.create_tasks_from_production_graph(graph, priority_map)
        
        # Should create 2 tasks
        assert len(tasks) == 2
        
        # Check task properties
        iron_task_id = integrator.node_to_task_map["iron"]
        steel_task_id = integrator.node_to_task_map["steel"]
        
        iron_task = integrator.priority_calc.get_task(iron_task_id)
        steel_task = integrator.priority_calc.get_task(steel_task_id)
        
        assert iron_task.name == "Iron Production"
        assert iron_task.base_priority == 1.0
        assert iron_task.task_type == "resource_production"
        
        assert steel_task.name == "Steel Production"
        assert steel_task.base_priority == 3.0
        assert steel_task.task_type == "refined_production"
        
        # Check dependencies
        assert iron_task_id in steel_task.upstream_dependencies
        assert steel_task_id in iron_task.downstream_dependents
    
    def test_inventory_graph_integration(self):
        """Test converting an inventory graph to tasks."""
        integrator = GraphTaskIntegrator()
        
        # Create simple inventory graph
        inv_graph = InventoryGraph()
        
        node1 = InventoryNode("factory", "Steel Factory")
        node1.status = "critical"  # Should be marked as blocked
        node1.inventory = {"steel": 10}
        node1.delta = {"steel": -50}  # High demand
        
        node2 = InventoryNode("depot", "Supply Depot")
        node2.status = "ok"
        node2.inventory = {"rifles": 20}
        node2.delta = {"rifles": -10}
        
        inv_graph.add_node(node1)
        inv_graph.add_node(node2)
        inv_graph.add_edge("factory", "depot", allowed_items=["steel"])
        
        tasks = integrator.create_tasks_from_inventory_graph(inv_graph)
        
        # Should create 2 tasks
        assert len(tasks) == 2
        
        # Check factory task (should be blocked due to critical status)
        factory_task_id = integrator.node_to_task_map["factory"]
        factory_task = integrator.priority_calc.get_task(factory_task_id)
        
        assert factory_task.name == "Supply Steel Factory"
        assert factory_task.status == TaskStatus.BLOCKED
        assert factory_task.task_type == "supply"
        assert factory_task.base_priority > 2.0  # Should have elevated priority due to critical status
        
        # Check depot task
        depot_task_id = integrator.node_to_task_map["depot"]
        depot_task = integrator.priority_calc.get_task(depot_task_id)
        
        assert depot_task.name == "Supply Supply Depot"
        assert depot_task.status == TaskStatus.PENDING
        
        # Check dependencies
        assert factory_task_id in depot_task.upstream_dependencies
    
    def test_mark_production_blocked_unblocked(self):
        """Test marking production nodes as blocked and unblocked."""
        integrator = GraphTaskIntegrator()
        
        # Create simple graph
        graph = nx.DiGraph()
        graph.add_node("iron", node=type('MockNode', (), {'name': 'Iron', 'category': 'resource'})())
        tasks = integrator.create_tasks_from_production_graph(graph)
        
        # Initially not blocked
        iron_task_id = integrator.node_to_task_map["iron"]
        iron_task = integrator.priority_calc.get_task(iron_task_id)
        assert iron_task.status == TaskStatus.PENDING
        
        # Mark as blocked
        result = integrator.mark_production_blocked("iron", "Test blockage")
        assert result is True
        assert iron_task.status == TaskStatus.BLOCKED
        assert iron_task.metadata.get("block_reason") == "Test blockage"
        
        # Mark as unblocked
        result = integrator.mark_production_unblocked("iron")
        assert result is True
        assert iron_task.status == TaskStatus.PENDING
        assert "block_reason" not in iron_task.metadata
        
        # Test with non-existent node
        result = integrator.mark_production_blocked("nonexistent", "Test")
        assert result is False
    
    def test_priority_recommendations(self):
        """Test getting priority recommendations."""
        integrator = GraphTaskIntegrator()
        
        # Create graph with blocked dependency
        graph = nx.DiGraph()
        
        class MockNode:
            def __init__(self, name, category):
                self.name = name
                self.category = category
        
        graph.add_node("iron", node=MockNode("Iron", "resource"))
        graph.add_node("steel", node=MockNode("Steel", "refined"))
        graph.add_edge("iron", "steel")
        
        priority_map = {"iron": 1.0, "steel": 5.0}
        tasks = integrator.create_tasks_from_production_graph(graph, priority_map)
        
        # Block iron production
        integrator.mark_production_blocked("iron", "Resource shortage")
        
        # Get recommendations
        recommendations = integrator.get_priority_recommendations(5)
        
        assert len(recommendations) == 2
        
        # Steel should have higher priority due to blocked dependency
        steel_rec = next(rec for rec in recommendations if rec[0] == "steel")
        iron_rec = next(rec for rec in recommendations if rec[0] == "iron")
        
        assert steel_rec[2] > iron_rec[2]  # Steel priority > Iron priority
        assert steel_rec[3]["blocked_count"] == 1  # Steel has 1 blocked upstream task
    
    def test_priority_report_generation(self):
        """Test generating a priority report."""
        integrator = GraphTaskIntegrator()
        
        # Create simple graph
        graph = nx.DiGraph()
        graph.add_node("test", node=type('MockNode', (), {'name': 'Test Node', 'category': 'resource'})())
        tasks = integrator.create_tasks_from_production_graph(graph)
        
        # Generate report
        report = integrator.generate_priority_report()
        
        # Check report contains expected sections
        assert "FLUID DYNAMICS PRIORITY REPORT" in report
        assert "Total tasks analyzed: 1" in report
        assert "Currently blocked tasks: 0" in report
        assert "TOP PRIORITY RECOMMENDATIONS:" in report
        assert "CRITICAL BOTTLENECKS:" in report
    
    def test_default_priority_calculation(self):
        """Test default priority calculation methods."""
        integrator = GraphTaskIntegrator()
        
        # Test task type priorities
        assert integrator._get_default_priority_by_type("resource_production") == 1.0
        assert integrator._get_default_priority_by_type("refined_production") == 2.0
        assert integrator._get_default_priority_by_type("material_production") == 3.0
        assert integrator._get_default_priority_by_type("product_production") == 4.0
        assert integrator._get_default_priority_by_type("unknown_type") == 1.0
        
        # Test inventory status priorities
        mock_node = type('MockNode', (), {
            'status': 'critical',
            'delta': {'item1': -10, 'item2': 5}  # High demand for item1
        })()
        
        priority = integrator._get_priority_from_inventory_status(mock_node)
        assert priority > 2.0  # Should be elevated due to critical status and demand
    
    def test_graph_without_node_objects(self):
        """Test handling graphs without node objects."""
        integrator = GraphTaskIntegrator()
        
        # Create graph with just node IDs (no node objects)
        graph = nx.DiGraph()
        graph.add_node("basic_node")
        
        tasks = integrator.create_tasks_from_production_graph(graph)
        
        assert len(tasks) == 1
        task = tasks[0]
        assert task.name == "basic_node"  # Should use node ID as name
        assert task.task_type == "production"  # Default task type
        assert task.base_priority == 1.0  # Default priority


if __name__ == "__main__":
    pytest.main([__file__])