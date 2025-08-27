"""
Tests for the transportation cost algorithm and integration.
"""
import pytest
import sys
import os

# Add the project root to the Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transportation_cost import (
    VehicleType, VehicleTemplate, CustomVehicle, Route, NetworkDecisionEngine,
    TransportationMode, create_default_decision_engine, integrate_with_inventory_edge
)
from services.inventory.inventory_graph import InventoryGraph, InventoryNode, InventoryEdge


class TestVehicleTemplate:
    """Test VehicleTemplate class functionality."""
    
    def test_vehicle_template_creation(self):
        """Test basic vehicle template creation."""
        template = VehicleTemplate(
            vehicle_type=VehicleType.BASE_TRUCK,
            name="Test Truck",
            inventory_slots=15,
            crate_capacity=5,
            shippable_capacity=1
        )
        
        assert template.vehicle_type == VehicleType.BASE_TRUCK
        assert template.name == "Test Truck"
        assert template.inventory_slots == 15
        assert template.crate_capacity == 5
        assert template.shippable_capacity == 1
        
    def test_vehicle_template_capacity(self):
        """Test vehicle template capacity calculation."""
        template = VehicleTemplate(
            vehicle_type=VehicleType.FREIGHTER,
            name="Test Freighter",
            inventory_slots=0,
            crate_capacity=10,
            shippable_capacity=5
        )
        
        capacity = template.get_total_capacity()
        expected = {
            "inventory_slots": 0,
            "crates": 10,
            "shippables": 5
        }
        assert capacity == expected


class TestCustomVehicle:
    """Test CustomVehicle class functionality."""
    
    def test_custom_vehicle_with_overrides(self):
        """Test custom vehicle with capacity overrides."""
        template = VehicleTemplate(
            vehicle_type=VehicleType.BASE_TRUCK,
            name="Base Truck",
            inventory_slots=15
        )
        
        custom = CustomVehicle(
            template=template,
            custom_name="Modified Truck",
            custom_inventory_slots=20
        )
        
        capacity = custom.get_effective_capacity()
        assert capacity["inventory_slots"] == 20  # Override applied
        assert capacity["crates"] == 0  # From template
        assert capacity["shippables"] == 0  # From template
        
    def test_custom_vehicle_no_overrides(self):
        """Test custom vehicle using template defaults."""
        template = VehicleTemplate(
            vehicle_type=VehicleType.FLATBED,
            name="Flatbed",
            inventory_slots=1,
            shippable_capacity=1
        )
        
        custom = CustomVehicle(template=template, custom_name="Standard Flatbed")
        capacity = custom.get_effective_capacity()
        
        assert capacity["inventory_slots"] == 1
        assert capacity["shippables"] == 1
        assert capacity["crates"] == 0


class TestRoute:
    """Test Route class functionality."""
    
    def test_route_creation(self):
        """Test basic route creation."""
        route = Route(
            source_node_id="depot_a",
            target_node_id="depot_b",
            allowed_vehicle_types=[VehicleType.BASE_TRUCK],
            regular_vehicle_time=2.5,
            flatbed_time=3.0
        )
        
        assert route.source_node_id == "depot_a"
        assert route.target_node_id == "depot_b"
        assert VehicleType.BASE_TRUCK in route.allowed_vehicle_types
        assert route.regular_vehicle_time == 2.5
        assert route.flatbed_time == 3.0
        
    def test_route_transport_time(self):
        """Test route transport time calculation."""
        route = Route(
            source_node_id="a",
            target_node_id="b",
            regular_vehicle_time=2.0,
            flatbed_time=2.5
        )
        
        # Test flatbed time
        assert route.get_transport_time(VehicleType.FLATBED) == 2.5
        
        # Test regular vehicle time
        assert route.get_transport_time(VehicleType.BASE_TRUCK) == 2.0
        
        # Test custom time
        route.custom_times["specialized_truck"] = 1.8
        assert route.get_transport_time(VehicleType.SPECIALIZED_TRUCK) == 1.8
        
    def test_route_no_time_data(self):
        """Test route with no time data."""
        route = Route(source_node_id="a", target_node_id="b")
        
        assert route.get_transport_time(VehicleType.BASE_TRUCK) is None
        assert route.get_transport_time(VehicleType.FLATBED) is None


class TestNetworkDecisionEngine:
    """Test NetworkDecisionEngine class functionality."""
    
    def test_decision_engine_creation(self):
        """Test decision engine creation with default templates."""
        engine = NetworkDecisionEngine()
        
        assert engine.enable_transportation is True
        assert VehicleType.BASE_TRUCK in engine.vehicle_templates
        assert VehicleType.FLATBED_TRAIN in engine.vehicle_templates
        assert VehicleType.FREIGHTER in engine.vehicle_templates
        
    def test_decision_engine_disabled(self):
        """Test decision engine with transportation disabled."""
        engine = NetworkDecisionEngine(enable_transportation=False)
        
        decision = engine.should_transport_vs_produce(
            item="rifle",
            quantity=10,
            source_id="a",
            target_id="b"
        )
        
        assert decision["decision"] == "produce"
        assert "disabled" in decision["reason"].lower()
        assert decision["confidence"] == 1.0
        
    def test_decision_no_route(self):
        """Test decision when no route is configured."""
        engine = NetworkDecisionEngine()
        
        decision = engine.should_transport_vs_produce(
            item="rifle",
            quantity=10,
            source_id="a",
            target_id="b"
        )
        
        assert decision["decision"] == "produce"
        assert "no transportation route" in decision["reason"].lower()
        
    def test_decision_with_route_and_times(self):
        """Test decision with configured route and time data."""
        engine = NetworkDecisionEngine()
        
        route = Route(
            source_node_id="depot",
            target_node_id="front",
            regular_vehicle_time=2.0
        )
        engine.add_route(route)
        
        # Transport should be faster than production
        decision = engine.should_transport_vs_produce(
            item="rifle",
            quantity=10,
            source_id="depot",
            target_id="front",
            production_time=4.0,
            vehicle_type=VehicleType.BASE_TRUCK
        )
        
        assert decision["decision"] == "transport"
        assert decision["transport_time"] == 2.0
        assert decision["production_time"] == 4.0
        assert "faster than production" in decision["reason"].lower()
        
    def test_decision_production_faster(self):
        """Test decision when production is faster than transport."""
        engine = NetworkDecisionEngine()
        
        route = Route(
            source_node_id="depot",
            target_node_id="front",
            regular_vehicle_time=5.0
        )
        engine.add_route(route)
        
        decision = engine.should_transport_vs_produce(
            item="rifle",
            quantity=10,
            source_id="depot",
            target_id="front",
            production_time=2.0,
            vehicle_type=VehicleType.BASE_TRUCK
        )
        
        assert decision["decision"] == "produce"
        assert "faster than transport" in decision["reason"].lower()
        
    def test_surplus_adjustment(self):
        """Test surplus inventory adjustment in transport time."""
        engine = NetworkDecisionEngine()
        
        route = Route(
            source_node_id="depot",
            target_node_id="front",
            regular_vehicle_time=4.0
        )
        engine.add_route(route)
        
        # With surplus covering half the need
        decision = engine.should_transport_vs_produce(
            item="rifle",
            quantity=20,
            source_id="depot",
            target_id="front",
            production_time=5.0,
            current_surplus=10,  # Half the needed amount
            vehicle_type=VehicleType.BASE_TRUCK
        )
        
        # Transport time should be reduced due to surplus
        assert decision["transport_time"] < 4.0
        assert decision["surplus_adjustment"] is True
        
    def test_capacity_efficiency(self):
        """Test capacity efficiency calculation."""
        engine = NetworkDecisionEngine()
        
        items = {"rifle": 10, "ammo": 5}
        storage_types = {"rifle": "inventory", "ammo": "inventory"}
        
        efficiency = engine.calculate_capacity_efficiency(
            VehicleType.BASE_TRUCK,
            items,
            storage_types
        )
        
        assert "overall_efficiency" in efficiency
        assert "can_transport" in efficiency
        assert efficiency["vehicle_type"] == "base_truck"
        assert efficiency["can_transport"] is True  # Should fit in 15 slot truck
        
    def test_capacity_over_limit(self):
        """Test capacity efficiency when over vehicle limits."""
        engine = NetworkDecisionEngine()
        
        items = {"rifle": 20}  # More than 15 slot capacity
        storage_types = {"rifle": "inventory"}
        
        efficiency = engine.calculate_capacity_efficiency(
            VehicleType.BASE_TRUCK,
            items,
            storage_types
        )
        
        assert efficiency["can_transport"] is False
        assert efficiency["overall_efficiency"] > 1.0  # Over capacity


class TestInventoryEdgeIntegration:
    """Test integration with InventoryEdge class."""
    
    def test_transportation_config_integration(self):
        """Test setting and getting transportation config on edges."""
        node1 = InventoryNode("n1", "Location A")
        node2 = InventoryNode("n2", "Location B")
        edge = InventoryEdge(node1, node2)
        
        transport_config = {
            "transportation_enabled": True,
            "vehicle_types": ["base_truck", "flatbed"],
            "transport_times": {"base_truck": 2.0, "flatbed": 2.5}
        }
        
        edge.set_transportation_config(transport_config)
        
        assert edge.is_transportation_enabled() is True
        assert edge.get_transport_time("base_truck") == 2.0
        assert edge.get_transport_time("flatbed") == 2.5
        assert edge.get_transport_time("nonexistent") is None
        
    def test_transportation_disabled_edge(self):
        """Test edge with transportation disabled."""
        node1 = InventoryNode("n1", "Location A")
        node2 = InventoryNode("n2", "Location B")
        edge = InventoryEdge(node1, node2)
        
        assert edge.is_transportation_enabled() is False
        assert edge.get_transport_time("base_truck") is None
        
    def test_user_config_integration(self):
        """Test integration with existing user_config."""
        existing_config = {"priority": "high", "notes": "Important route"}
        
        updated_config = integrate_with_inventory_edge(existing_config)
        
        assert "transportation_cost" in updated_config
        assert updated_config["priority"] == "high"  # Existing config preserved
        assert updated_config["notes"] == "Important route"


class TestDefaultTemplates:
    """Test default vehicle templates."""
    
    def test_default_engine_templates(self):
        """Test that default engine has all expected templates."""
        engine = create_default_decision_engine()
        
        # Check all expected vehicle types are present
        expected_types = [
            VehicleType.FLATBED_TRAIN,
            VehicleType.FREIGHTER,
            VehicleType.FLATBED,
            VehicleType.BASE_TRUCK,
            VehicleType.SPECIALIZED_TRUCK
        ]
        
        for vehicle_type in expected_types:
            assert vehicle_type in engine.vehicle_templates
            template = engine.vehicle_templates[vehicle_type]
            assert template.name is not None
            assert template.vehicle_type == vehicle_type
            
    def test_flatbed_train_capacity(self):
        """Test flatbed train specific capacity."""
        engine = create_default_decision_engine()
        template = engine.vehicle_templates[VehicleType.FLATBED_TRAIN]
        
        assert template.shippable_capacity == 1  # 1 per car
        assert template.max_units == 15  # Max 15 cars
        
    def test_freighter_capacity(self):
        """Test freighter specific capacity."""
        engine = create_default_decision_engine()
        template = engine.vehicle_templates[VehicleType.FREIGHTER]
        
        assert template.shippable_capacity == 5
        assert template.crate_capacity == 10


class TestEndToEndScenario:
    """Test complete end-to-end transportation cost scenarios."""
    
    def test_complete_graph_with_transportation(self):
        """Test complete inventory graph with transportation costs."""
        # Create inventory graph
        graph = InventoryGraph()
        depot = InventoryNode("depot", "Main Depot")
        front = InventoryNode("front", "Frontline")
        graph.add_node(depot)
        graph.add_node(front)
        
        # Add edge with transportation configuration
        graph.add_edge("depot", "front", allowed_items=["rifle", "ammo"])
        edge = graph.edges[0]
        
        transport_config = {
            "transportation_enabled": True,
            "vehicle_types": ["base_truck"],
            "transport_times": {"base_truck": 3.0}
        }
        edge.set_transportation_config(transport_config)
        
        # Create decision engine
        engine = create_default_decision_engine()
        route = Route(
            source_node_id="depot",
            target_node_id="front",
            regular_vehicle_time=3.0
        )
        engine.add_route(route)
        
        # Test decision making
        decision = engine.should_transport_vs_produce(
            item="rifle",
            quantity=20,
            source_id="depot",
            target_id="front",
            production_time=6.0,  # Production takes longer
            current_surplus=5
        )
        
        assert decision["decision"] == "transport"
        assert decision["transport_time"] < 3.0  # Reduced due to surplus
        assert decision["confidence"] > 0.8
        
    def test_fallback_to_production(self):
        """Test fallback to production when transportation not viable."""
        engine = create_default_decision_engine()
        
        # No route configured - should fallback to production
        decision = engine.should_transport_vs_produce(
            item="rifle",
            quantity=20,
            source_id="unknown_depot",
            target_id="front",
            production_time=4.0
        )
        
        assert decision["decision"] == "produce"
        assert "no transportation route" in decision["reason"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])