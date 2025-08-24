#!/usr/bin/env python3
"""
Tests for the Network Onboarding CLI

This test suite validates the core functionality of the network onboarding tool,
including serialization, deserialization, and integration with existing graph classes.
"""

import pytest
import json
import yaml
import tempfile
import os
from pathlib import Path

# Import the CLI and required classes
from onboard_network import NetworkOnboardingCLI
from services.inventory.inventory_graph import InventoryGraph, InventoryNode
from services.inventory.production_nodes import FactoryNode, MassProductionFactoryNode, RefineryNode
from services.inventory.facility_node import FacilityNode
from services.inventory.base_types import BaseType
from services.FoxholeDataObjects.processes import ProductionType, FacilityType


class TestNetworkOnboardingCLI:
    """Test cases for NetworkOnboardingCLI"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.cli = NetworkOnboardingCLI()
    
    def test_cli_initialization(self):
        """Test CLI initializes correctly."""
        assert isinstance(self.cli.graph, InventoryGraph)
        assert self.cli.nodes == {}
        assert self.cli.next_node_id == 1
    
    def test_generate_node_id(self):
        """Test node ID generation."""
        first_id = self.cli._generate_node_id()
        second_id = self.cli._generate_node_id()
        
        assert first_id == "node_001"
        assert second_id == "node_002"
        assert self.cli.next_node_id == 3
    
    def test_create_mpf_node(self):
        """Test creating MPF node programmatically."""
        node_id = self.cli._generate_node_id()
        mpf_node = MassProductionFactoryNode(
            node_id=node_id,
            location_name="Test MPF",
            unit_size="crate",
            base_type=BaseType.PRODUCTION,
            production_type=ProductionType.MPF
        )
        
        mpf_node.metadata.update({
            "facility_type": "MPF",
            "description": "Mass Production Facility"
        })
        
        self.cli.nodes[node_id] = mpf_node
        self.cli.graph.add_node(mpf_node)
        
        assert node_id in self.cli.nodes
        assert mpf_node.location_name == "Test MPF"
        assert mpf_node.metadata["facility_type"] == "MPF"
        assert isinstance(mpf_node, MassProductionFactoryNode)
    
    def test_create_refinery_node(self):
        """Test creating refinery node programmatically."""
        node_id = self.cli._generate_node_id()
        refinery_node = RefineryNode(
            node_id=node_id,
            location_name="Test Refinery",
            unit_size="crate",
            base_type=BaseType.REFINERY,
            production_type=ProductionType.FACILITY,
            facility_type=FacilityType.REFINERY
        )
        
        refinery_node.metadata.update({
            "facility_type": "Refinery",
            "refinery_type": "Basic Materials Refinery"
        })
        
        self.cli.nodes[node_id] = refinery_node
        self.cli.graph.add_node(refinery_node)
        
        assert node_id in self.cli.nodes
        assert refinery_node.location_name == "Test Refinery"
        assert refinery_node.metadata["facility_type"] == "Refinery"
        assert isinstance(refinery_node, RefineryNode)
    
    def test_create_factory_node(self):
        """Test creating factory node programmatically."""
        node_id = self.cli._generate_node_id()
        factory_node = FactoryNode(
            node_id=node_id,
            location_name="Test Factory",
            unit_size="crate",
            base_type=BaseType.PRODUCTION,
            production_type=ProductionType.FACTORY
        )
        
        factory_node.metadata.update({
            "facility_type": "Factory",
            "factory_type": "Small Arms Factory"
        })
        
        self.cli.nodes[node_id] = factory_node
        self.cli.graph.add_node(factory_node)
        
        assert node_id in self.cli.nodes
        assert factory_node.location_name == "Test Factory"
        assert factory_node.metadata["facility_type"] == "Factory"
        assert isinstance(factory_node, FactoryNode)
    
    def test_create_facility_node(self):
        """Test creating facility node programmatically."""
        node_id = self.cli._generate_node_id()
        facility_node = FacilityNode(
            node_id=node_id,
            location_name="Test Depot",
            unit_size="crate",
            base_type=BaseType.FACILITY,
            production_type=ProductionType.FACILITY
        )
        
        facility_node.metadata.update({
            "facility_type": "Storage Depot",
            "description": "Storage Depot at Test Location"
        })
        
        self.cli.nodes[node_id] = facility_node
        self.cli.graph.add_node(facility_node)
        
        assert node_id in self.cli.nodes
        assert facility_node.location_name == "Test Depot"
        assert facility_node.metadata["facility_type"] == "Storage Depot"
        assert isinstance(facility_node, FacilityNode)
    
    def test_add_connections(self):
        """Test adding connections between nodes."""
        # Create two nodes
        node1_id = self.cli._generate_node_id()
        node1 = FactoryNode(
            node_id=node1_id,
            location_name="Factory A",
            unit_size="crate",
            base_type=BaseType.PRODUCTION,
            production_type=ProductionType.FACTORY
        )
        
        node2_id = self.cli._generate_node_id()
        node2 = FacilityNode(
            node_id=node2_id,
            location_name="Depot B",
            unit_size="crate",
            base_type=BaseType.FACILITY,
            production_type=ProductionType.FACILITY
        )
        
        self.cli.nodes[node1_id] = node1
        self.cli.nodes[node2_id] = node2
        self.cli.graph.add_node(node1)
        self.cli.graph.add_node(node2)
        
        # Add connection
        allowed_items = ["rifle", "ammo"]
        self.cli.graph.add_edge(node1_id, node2_id, allowed_items=allowed_items)
        
        assert len(self.cli.graph.edges) == 1
        edge = self.cli.graph.edges[0]
        assert edge.source == node1
        assert edge.target == node2
        assert edge.allowed_items == allowed_items
    
    def test_frontline_status(self):
        """Test setting frontline status."""
        node_id = self.cli._generate_node_id()
        node = FactoryNode(
            node_id=node_id,
            location_name="Frontline Factory",
            unit_size="crate",
            base_type=BaseType.PRODUCTION,
            production_type=ProductionType.FACTORY
        )
        
        # Set frontline status
        node.metadata["frontline"] = True
        
        self.cli.nodes[node_id] = node
        self.cli.graph.add_node(node)
        
        assert node.metadata["frontline"] is True
    
    def test_network_serialization_json(self):
        """Test serializing network to JSON."""
        # Create a simple network
        self._create_test_network()
        
        # Serialize to JSON
        network_data = self.cli._serialize_network()
        
        assert "metadata" in network_data
        assert "nodes" in network_data
        assert "edges" in network_data
        assert network_data["metadata"]["version"] == "1.0"
        assert len(network_data["nodes"]) == 2
        assert len(network_data["edges"]) == 1
    
    def test_network_serialization_yaml(self):
        """Test saving network as YAML file."""
        # Create a simple network
        self._create_test_network()
        
        # Save to temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            self.cli._save_yaml(temp_path)
            
            # Verify file exists and contains valid YAML
            assert os.path.exists(temp_path)
            with open(temp_path, 'r') as f:
                data = yaml.safe_load(f)
            
            assert "metadata" in data
            assert "nodes" in data
            assert "edges" in data
            assert len(data["nodes"]) == 2
            assert len(data["edges"]) == 1
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_network_deserialization(self):
        """Test loading network from serialized data."""
        # Create and serialize a network
        self._create_test_network()
        network_data = self.cli._serialize_network()
        
        # Create new CLI instance and deserialize
        new_cli = NetworkOnboardingCLI()
        success = new_cli._deserialize_network(network_data)
        
        assert success is True
        assert len(new_cli.nodes) == 2
        assert len(new_cli.graph.edges) == 1
        
        # Verify node types are preserved
        nodes = list(new_cli.nodes.values())
        factory_node = next(n for n in nodes if n.metadata.get("facility_type") == "Factory")
        depot_node = next(n for n in nodes if n.metadata.get("facility_type") == "Storage Depot")
        
        assert isinstance(factory_node, FactoryNode)
        assert isinstance(depot_node, FacilityNode)
        assert factory_node.metadata.get("frontline") is True
    
    def test_load_save_roundtrip_yaml(self):
        """Test complete save/load roundtrip with YAML."""
        # Create test network
        self._create_test_network()
        original_nodes = len(self.cli.nodes)
        original_edges = len(self.cli.graph.edges)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            self.cli._save_yaml(temp_path)
            
            # Load into new CLI instance
            new_cli = NetworkOnboardingCLI()
            success = new_cli.load_network(temp_path)
            
            assert success is True
            assert len(new_cli.nodes) == original_nodes
            assert len(new_cli.graph.edges) == original_edges
            
            # Verify specific data preservation
            nodes = list(new_cli.nodes.values())
            frontline_nodes = [n for n in nodes if n.metadata.get("frontline")]
            assert len(frontline_nodes) == 1
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_load_save_roundtrip_json(self):
        """Test complete save/load roundtrip with JSON."""
        # Create test network
        self._create_test_network()
        original_nodes = len(self.cli.nodes)
        original_edges = len(self.cli.graph.edges)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.cli._save_json(temp_path)
            
            # Load into new CLI instance
            new_cli = NetworkOnboardingCLI()
            success = new_cli.load_network(temp_path)
            
            assert success is True
            assert len(new_cli.nodes) == original_nodes
            assert len(new_cli.graph.edges) == original_edges
            
            # Verify specific data preservation
            nodes = list(new_cli.nodes.values())
            frontline_nodes = [n for n in nodes if n.metadata.get("frontline")]
            assert len(frontline_nodes) == 1
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_invalid_file_format(self):
        """Test loading invalid file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name
            f.write("invalid data")
        
        try:
            success = self.cli.load_network(temp_path)
            assert success is False
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_load_nonexistent_file(self):
        """Test loading nonexistent file."""
        success = self.cli.load_network("nonexistent_file.yaml")
        assert success is False
    
    def test_graph_integration(self):
        """Test integration with existing graph classes."""
        # Create network using CLI
        self._create_test_network()
        
        # Verify integration with InventoryGraph
        assert isinstance(self.cli.graph, InventoryGraph)
        
        # Test graph operations
        nodes = self.cli.graph.nodes
        assert len(nodes) == 2
        
        # Test finding nodes
        factory_id = next(id for id, node in self.cli.nodes.items() 
                         if node.metadata.get("facility_type") == "Factory")
        factory_node = self.cli.graph.get_node(factory_id)
        assert factory_node is not None
        assert isinstance(factory_node, FactoryNode)
        
        # Test edges
        edges = self.cli.graph.get_edges()
        assert len(edges) == 1
        assert edges[0].allowed_items == ["rifle", "ammo"]
    
    def _create_test_network(self):
        """Helper method to create a test network."""
        # Create factory node
        factory_id = self.cli._generate_node_id()
        factory_node = FactoryNode(
            node_id=factory_id,
            location_name="Test Factory",
            unit_size="crate",
            base_type=BaseType.PRODUCTION,
            production_type=ProductionType.FACTORY
        )
        factory_node.metadata.update({
            "facility_type": "Factory",
            "factory_type": "Small Arms Factory",
            "frontline": True
        })
        
        # Create depot node
        depot_id = self.cli._generate_node_id()
        depot_node = FacilityNode(
            node_id=depot_id,
            location_name="Test Depot",
            unit_size="crate",
            base_type=BaseType.FACILITY,
            production_type=ProductionType.FACILITY
        )
        depot_node.metadata.update({
            "facility_type": "Storage Depot",
            "frontline": False
        })
        
        # Add nodes to CLI
        self.cli.nodes[factory_id] = factory_node
        self.cli.nodes[depot_id] = depot_node
        self.cli.graph.add_node(factory_node)
        self.cli.graph.add_node(depot_node)
        
        # Add connection
        self.cli.graph.add_edge(factory_id, depot_id, allowed_items=["rifle", "ammo"])


# Integration test for the entire workflow
def test_cli_workflow_integration():
    """Integration test simulating the complete CLI workflow."""
    cli = NetworkOnboardingCLI()
    
    # Simulate creating an MPF
    mpf_id = cli._generate_node_id()
    mpf_node = MassProductionFactoryNode(
        node_id=mpf_id,
        location_name="Westgate MPF",
        unit_size="crate",
        base_type=BaseType.PRODUCTION,
        production_type=ProductionType.MPF
    )
    mpf_node.metadata.update({
        "facility_type": "MPF",
        "description": "Mass Production Facility"
    })
    cli.nodes[mpf_id] = mpf_node
    cli.graph.add_node(mpf_node)
    
    # Simulate creating a refinery
    refinery_id = cli._generate_node_id()
    refinery_node = RefineryNode(
        node_id=refinery_id,
        location_name="Heartlands Refinery",
        unit_size="crate",
        base_type=BaseType.REFINERY,
        production_type=ProductionType.FACILITY,
        facility_type=FacilityType.REFINERY
    )
    refinery_node.metadata.update({
        "facility_type": "Refinery",
        "refinery_type": "Basic Materials Refinery"
    })
    cli.nodes[refinery_id] = refinery_node
    cli.graph.add_node(refinery_node)
    
    # Create factory and depot
    factory_id = cli._generate_node_id()
    factory_node = FactoryNode(
        node_id=factory_id,
        location_name="Frontline Factory",
        unit_size="crate",
        base_type=BaseType.PRODUCTION,
        production_type=ProductionType.FACTORY
    )
    factory_node.metadata.update({
        "facility_type": "Factory",
        "factory_type": "Small Arms Factory",
        "frontline": True
    })
    cli.nodes[factory_id] = factory_node
    cli.graph.add_node(factory_node)
    
    depot_id = cli._generate_node_id()
    depot_node = FacilityNode(
        node_id=depot_id,
        location_name="Supply Depot",
        unit_size="crate",
        base_type=BaseType.FACILITY,
        production_type=ProductionType.FACILITY
    )
    depot_node.metadata.update({
        "facility_type": "Storage Depot"
    })
    cli.nodes[depot_id] = depot_node
    cli.graph.add_node(depot_node)
    
    # Add connections: Refinery -> MPF -> Factory -> Depot
    cli.graph.add_edge(refinery_id, mpf_id, allowed_items=["bmats", "emats"])
    cli.graph.add_edge(mpf_id, factory_id, allowed_items=["rifles", "ammo"])
    cli.graph.add_edge(factory_id, depot_id, allowed_items=["rifles", "ammo"])
    
    # Verify the network
    assert len(cli.nodes) == 4
    assert len(cli.graph.edges) == 3
    
    # Verify node types
    assert isinstance(cli.nodes[mpf_id], MassProductionFactoryNode)
    assert isinstance(cli.nodes[refinery_id], RefineryNode)
    assert isinstance(cli.nodes[factory_id], FactoryNode)
    assert isinstance(cli.nodes[depot_id], FacilityNode)
    
    # Verify frontline status
    assert cli.nodes[factory_id].metadata.get("frontline") is True
    assert cli.nodes[depot_id].metadata.get("frontline") is not True
    
    # Test serialization
    network_data = cli._serialize_network()
    assert len(network_data["nodes"]) == 4
    assert len(network_data["edges"]) == 3
    
    # Test deserialization
    new_cli = NetworkOnboardingCLI()
    success = new_cli._deserialize_network(network_data)
    assert success is True
    assert len(new_cli.nodes) == 4
    assert len(new_cli.graph.edges) == 3
    
    # Verify preservation of node types after deserialization
    nodes_by_type = {}
    for node in new_cli.nodes.values():
        facility_type = node.metadata.get("facility_type")
        nodes_by_type[facility_type] = node
    
    assert "MPF" in nodes_by_type
    assert "Refinery" in nodes_by_type
    assert "Factory" in nodes_by_type
    assert "Storage Depot" in nodes_by_type
    
    print("✅ Integration test passed - CLI workflow works correctly!")


if __name__ == "__main__":
    # Run integration test if script is executed directly
    test_cli_workflow_integration()