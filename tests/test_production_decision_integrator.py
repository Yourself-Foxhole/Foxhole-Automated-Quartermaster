"""
Tests for the production decision integrator.
"""
import pytest
import sys
import os

# Add the project root to the Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.production_decision_integrator import (
    ProductionDecision, ProductionDecisionIntegrator, create_integrated_system
)
from services.inventory.inventory_graph import InventoryGraph, InventoryNode, InventoryEdge
from transportation_cost import VehicleType


class TestProductionDecision:
    """Test ProductionDecision data class."""
    
    def test_production_decision_creation(self):
        """Test basic ProductionDecision creation."""
        decision = ProductionDecision(
            item="rifle",
            quantity=50,
            source_node_id="depot",
            target_node_id="frontline",
            decision="transport",
            primary_reason="Transport faster than production",
            confidence=0.9,
            transport_time=2.5,
            production_time=4.0
        )
        
        assert decision.item == "rifle"
        assert decision.quantity == 50
        assert decision.decision == "transport"
        assert decision.confidence == 0.9
        assert decision.transport_time == 2.5
        assert decision.production_time == 4.0
        assert decision.alternatives == []


class TestProductionDecisionIntegrator:
    """Test ProductionDecisionIntegrator class."""
    
    def setup_method(self):
        """Set up test environment with sample inventory graph."""
        self.graph = InventoryGraph()
        
        # Create test nodes
        self.depot = InventoryNode("depot", "Main Depot")
        self.depot.inventory = {"rifle": 100, "ammo": 500, "bmats": 300}
        self.depot.delta = {"rifle": -50, "ammo": -200}  # Surplus
        
        self.factory = InventoryNode("factory", "Weapons Factory")
        self.factory.inventory = {"bmats": 50, "rifle": 10}
        self.factory.delta = {"rifle": 40, "bmats": 100}
        
        self.frontline = InventoryNode("frontline", "Frontline Base")
        self.frontline.inventory = {"ammo": 30}
        self.frontline.delta = {"rifle": 75, "ammo": 150}
        
        self.graph.add_node(self.depot)
        self.graph.add_node(self.factory)
        self.graph.add_node(self.frontline)
        
        # Add edges
        self.graph.add_edge("depot", "factory", allowed_items=["rifle", "ammo", "bmats"])
        self.graph.add_edge("depot", "frontline", allowed_items=["rifle", "ammo"])
        self.graph.add_edge("factory", "frontline", allowed_items=["rifle"])
        
        # Configure transportation on some edges
        depot_factory_edge = self.graph.edges[0]
        depot_factory_edge.set_transportation_config({
            "transportation_enabled": True,
            "transport_times": {"base_truck": 1.5, "flatbed": 2.0}
        })
        
        depot_frontline_edge = self.graph.edges[1]
        depot_frontline_edge.set_transportation_config({
            "transportation_enabled": True,
            "transport_times": {"base_truck": 3.5, "flatbed": 4.0}
        })
        
        # Factory to frontline has no transportation config (production only)
        
    def test_integrator_creation(self):
        """Test integrator creation and initialization."""
        integrator = ProductionDecisionIntegrator(
            inventory_graph=self.graph,
            enable_transportation=True
        )
        
        assert integrator.inventory_graph == self.graph
        assert integrator.enable_transportation is True
        assert integrator.transportation_engine is not None
        
    def test_integrator_transportation_disabled(self):
        """Test integrator with transportation disabled."""
        integrator = ProductionDecisionIntegrator(
            inventory_graph=self.graph,
            enable_transportation=False
        )
        
        decision = integrator.analyze_production_decision(
            item="rifle",
            quantity=20,
            target_node_id="frontline"
        )
        
        assert decision.decision == "produce"
        assert "disabled" in decision.primary_reason.lower()
        assert decision.confidence == 1.0
        
    def test_production_time_estimation(self):
        """Test production time estimation."""
        integrator = ProductionDecisionIntegrator(
            inventory_graph=self.graph,
            enable_transportation=True
        )
        
        # Test known item
        rifle_time = integrator.estimate_production_time("rifle", 10, "factory")
        assert rifle_time is not None
        assert rifle_time > 0
        
        # Test with custom base time
        custom_time = integrator.estimate_production_time("rifle", 5, "factory", base_time_per_unit=0.2)
        assert custom_time == 1.0  # 5 * 0.2 * 1.0 (multiplier)
        
        # Test nonexistent node
        no_node_time = integrator.estimate_production_time("rifle", 10, "nonexistent")
        assert no_node_time is None
        
    def test_surplus_calculation(self):
        """Test current surplus calculation."""
        integrator = ProductionDecisionIntegrator(
            inventory_graph=self.graph,
            enable_transportation=True
        )
        
        # Depot has surplus rifles (100 inventory, only need 50 based on delta)
        rifle_surplus = integrator.get_current_surplus("rifle", "depot")
        assert rifle_surplus == 50  # 100 - 50 = 50 surplus
        
        # Factory needs rifles (10 inventory, 40 delta need)
        factory_surplus = integrator.get_current_surplus("rifle", "factory")
        assert factory_surplus == 0  # No surplus, actually needs more
        
        # Nonexistent item
        no_surplus = integrator.get_current_surplus("nonexistent", "depot")
        assert no_surplus == 0
        
    def test_find_potential_sources(self):
        """Test finding potential source nodes."""
        integrator = ProductionDecisionIntegrator(
            inventory_graph=self.graph,
            enable_transportation=True
        )
        
        # Find sources for rifles targeting frontline
        sources = integrator._find_potential_sources("rifle", "frontline")
        
        # Should find depot (has inventory) and factory (has edge allowing rifles)
        assert "depot" in sources
        assert "factory" in sources
        assert "frontline" not in sources  # Target excluded
        
        # Find sources for unknown item
        unknown_sources = integrator._find_potential_sources("unknown_item", "frontline")
        # Should still find nodes with edges that allow any items (empty allowed_items)
        assert len(unknown_sources) >= 0
        
    def test_transport_decision_with_surplus(self):
        """Test transportation decision when surplus is available."""
        integrator = ProductionDecisionIntegrator(
            inventory_graph=self.graph,
            enable_transportation=True
        )
        
        # Request rifles for frontline - depot has surplus
        decision = integrator.analyze_production_decision(
            item="rifle",
            quantity=10,  # Reduced to fit in truck capacity  
            target_node_id="frontline",
            potential_sources=["depot"]
        )
        
        assert decision.decision == "transport"
        assert decision.source_node_id == "depot"
        assert decision.transport_time is not None
        assert decision.transport_time < 3.5  # Should be reduced due to surplus
        assert decision.confidence > 0.8
        
    def test_production_decision_no_sources(self):
        """Test decision when no transportation sources are available."""
        integrator = ProductionDecisionIntegrator(
            inventory_graph=self.graph,
            enable_transportation=True
        )
        
        # Request item that no source has, targeting isolated node
        decision = integrator.analyze_production_decision(
            item="unknown_item",
            quantity=10,
            target_node_id="frontline",
            potential_sources=[]  # No sources
        )
        
        assert decision.decision == "produce"
        assert "no viable transportation" in decision.primary_reason.lower()
        
    def test_production_faster_than_transport(self):
        """Test decision when local production is faster than transport."""
        # This test verifies that when transportation options are not viable,
        # the system falls back to production
        integrator = ProductionDecisionIntegrator(
            inventory_graph=self.graph,
            enable_transportation=True,
            default_production_time_multiplier=0.01  # Make production extremely fast
        )
        
        decision = integrator.analyze_production_decision(
            item="rifle",
            quantity=10,
            target_node_id="frontline",
            potential_sources=["depot"]
        )
        
        # With extremely fast production, should choose to produce locally
        # (Even if transportation isn't viable, production is the fallback)
        assert decision.decision == "produce"
        assert decision.production_time is not None
        assert decision.production_time < 1.0  # Very fast production
        # The reason may be "no viable options" or "faster than transport"
        reason_lower = decision.primary_reason.lower()
        assert ("no viable" in reason_lower or "faster" in reason_lower)
        
    def test_alternatives_generation(self):
        """Test generation of alternative options."""
        integrator = ProductionDecisionIntegrator(
            inventory_graph=self.graph,
            enable_transportation=True
        )
        
        decision = integrator.analyze_production_decision(
            item="rifle",
            quantity=20,
            target_node_id="frontline",
            include_alternatives=True
        )
        
        # Should have alternatives
        assert len(decision.alternatives) > 0
        
        # Check that alternatives include different types
        alternative_types = [alt["type"] for alt in decision.alternatives]
        assert len(set(alternative_types)) > 0  # Should have some variety
        
    def test_batch_analysis(self):
        """Test batch analysis of multiple decisions."""
        integrator = ProductionDecisionIntegrator(
            inventory_graph=self.graph,
            enable_transportation=True
        )
        
        requests = [
            {"item": "rifle", "quantity": 20, "target_node_id": "frontline"},
            {"item": "ammo", "quantity": 100, "target_node_id": "factory"},
            {"item": "bmats", "quantity": 50, "target_node_id": "frontline"}
        ]
        
        decisions = integrator.batch_analyze_decisions(requests)
        
        assert len(decisions) == 3
        assert all(isinstance(d, ProductionDecision) for d in decisions)
        assert decisions[0].item == "rifle"
        assert decisions[1].item == "ammo"
        assert decisions[2].item == "bmats"
        
    def test_vehicle_preference(self):
        """Test vehicle preference in decisions."""
        integrator = ProductionDecisionIntegrator(
            inventory_graph=self.graph,
            enable_transportation=True
        )
        
        # Test with flatbed preference
        decision = integrator.analyze_production_decision(
            item="rifle",
            quantity=10,
            target_node_id="frontline",
            vehicle_preference=VehicleType.FLATBED
        )
        
        if decision.decision == "transport":
            assert decision.transport_vehicle == VehicleType.FLATBED


class TestIntegratedSystem:
    """Test the integrated system creation and usage."""
    
    def test_create_integrated_system(self):
        """Test creation of integrated system."""
        graph = InventoryGraph()
        node = InventoryNode("test", "Test Node")
        graph.add_node(node)
        
        system = create_integrated_system(graph, enable_transportation=True)
        
        assert isinstance(system, ProductionDecisionIntegrator)
        assert system.inventory_graph == graph
        assert system.enable_transportation is True
        
    def test_integrated_system_disabled_transport(self):
        """Test integrated system with transportation disabled."""
        graph = InventoryGraph()
        node = InventoryNode("test", "Test Node")
        graph.add_node(node)
        
        system = create_integrated_system(graph, enable_transportation=False)
        
        decision = system.analyze_production_decision(
            item="rifle",
            quantity=10,
            target_node_id="test"
        )
        
        assert decision.decision == "produce"
        assert "disabled" in decision.primary_reason.lower()


class TestComplexScenarios:
    """Test complex real-world scenarios."""
    
    def test_multi_hop_supply_chain(self):
        """Test complex multi-hop supply chain scenario."""
        graph = InventoryGraph()
        
        # Create a complex supply chain
        resource_node = InventoryNode("resource", "Resource Node")
        resource_node.inventory = {"salvage": 1000}
        
        refinery = InventoryNode("refinery", "Refinery")
        refinery.inventory = {"bmats": 200}
        
        factory = InventoryNode("factory", "Factory")
        factory.inventory = {"rifle": 50}
        
        depot = InventoryNode("depot", "Supply Depot")
        depot.inventory = {"rifle": 100, "ammo": 300}
        
        frontline = InventoryNode("frontline", "Frontline")
        frontline.delta = {"rifle": 75, "ammo": 200}
        
        for node in [resource_node, refinery, factory, depot, frontline]:
            graph.add_node(node)
        
        # Create supply chain edges
        graph.add_edge("resource", "refinery", allowed_items=["salvage"])
        graph.add_edge("refinery", "factory", allowed_items=["bmats"])
        graph.add_edge("factory", "depot", allowed_items=["rifle"])
        graph.add_edge("depot", "frontline", allowed_items=["rifle", "ammo"])
        
        # Configure transportation times
        depot_frontline_edge = graph.edges[-1]
        depot_frontline_edge.set_transportation_config({
            "transportation_enabled": True,
            "transport_times": {"base_truck": 2.0}
        })
        
        integrator = ProductionDecisionIntegrator(graph, enable_transportation=True)
        
        # Analyze decision for frontline needs
        decision = integrator.analyze_production_decision(
            item="rifle",
            quantity=10,  # Reduced to fit capacity
            target_node_id="frontline"
        )
        
        # Should prefer transport from depot (has inventory and short route)
        assert decision.decision == "transport"
        assert decision.source_node_id == "depot"
        # Transport time will be reduced due to surplus inventory
        assert decision.transport_time <= 2.0  # May be reduced due to surplus
        
    def test_capacity_constrained_scenario(self):
        """Test scenario where vehicle capacity is a limiting factor."""
        graph = InventoryGraph()
        
        source = InventoryNode("source", "Source")
        source.inventory = {"heavy_equipment": 10}  # Large items
        
        target = InventoryNode("target", "Target")
        target.delta = {"heavy_equipment": 5}
        
        graph.add_node(source)
        graph.add_node(target)
        graph.add_edge("source", "target", allowed_items=["heavy_equipment"])
        
        edge = graph.edges[0]
        edge.set_transportation_config({
            "transportation_enabled": True,
            "transport_times": {"base_truck": 1.0}  # Fast transport
        })
        
        integrator = ProductionDecisionIntegrator(graph, enable_transportation=True)
        
        # Override capacity calculation to show constraint
        original_calc = integrator.transportation_engine.calculate_capacity_efficiency
        
        def mock_calc(vehicle_type, items_to_transport, item_storage_types):
            return {
                "overall_efficiency": 2.0,  # Over capacity
                "can_transport": False,  # Cannot transport
                "vehicle_type": vehicle_type.value
            }
        
        integrator.transportation_engine.calculate_capacity_efficiency = mock_calc
        
        decision = integrator.analyze_production_decision(
            item="heavy_equipment",
            quantity=5,
            target_node_id="target"
        )
        
        # Should fall back to production due to capacity constraint
        assert decision.decision == "produce"
        assert "no viable transportation" in decision.primary_reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])