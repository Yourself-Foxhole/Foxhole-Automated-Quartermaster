#!/usr/bin/env python3
"""
Network Onboarding CLI for Foxhole Logistics Graph

This tool provides an interactive CLI to onboard and configure a Foxhole logistics network.
It guides users through setting up core supply chain components (MPFs, refineries, factories,
facilities) and their connections, stores the network in human-readable format, and supports
loading/saving for debugging and simulation.
"""

import argparse
import json
import yaml
import sys
import os
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# Import existing graph classes
from services.inventory.inventory_graph import InventoryGraph, InventoryNode
from services.inventory.production_nodes import (
    ProductionNode, FactoryNode, MassProductionFactoryNode, 
    RefineryNode, QueueableProductionNode
)
from services.inventory.facility_node import FacilityNode
from services.inventory.base_types import BaseType
from services.FoxholeDataObjects.processes import (
    ProductionType, FacilityType, ProcessType, PRODUCTION_PROCESS_MAP
)


class NetworkOnboardingCLI:
    """Interactive CLI tool for onboarding Foxhole logistics networks."""
    
    def __init__(self):
        self.graph = InventoryGraph()
        self.nodes: Dict[str, InventoryNode] = {}
        self.next_node_id = 1
        
    def run(self):
        """Main entry point for the CLI."""
        print("=" * 60)
        print("Foxhole Automated Quartermaster - Network Onboarding")
        print("=" * 60)
        print("\nWelcome to the network onboarding wizard!")
        print("This tool will guide you through setting up your logistics network.")
        print("\nYou'll be prompted to add:")
        print("  1. MPF (Mass Production Facility)")
        print("  2. Refineries")
        print("  3. Factories")
        print("  4. Other Facilities")
        print("  5. Network connections")
        print()
        
        if not self._confirm("Ready to begin? (y/n): "):
            print("Onboarding cancelled.")
            return
            
        try:
            # Step-by-step onboarding
            self._onboard_mpfs()
            self._onboard_refineries()
            self._onboard_factories()
            self._onboard_facilities()
            self._configure_connections()
            self._configure_frontline_status()
            
            # Show summary and save
            self._show_network_summary()
            self._save_network()
            
            print("\n✅ Network onboarding completed successfully!")
            
        except KeyboardInterrupt:
            print("\n\nOnboarding interrupted by user.")
        except Exception as e:
            print(f"\n❌ Error during onboarding: {e}")
            raise

    def _confirm(self, prompt: str) -> bool:
        """Get yes/no confirmation from user."""
        while True:
            response = input(prompt).strip().lower()
            if response in ('y', 'yes'):
                return True
            elif response in ('n', 'no'):
                return False
            else:
                print("Please enter 'y' or 'n'")

    def _get_input(self, prompt: str, default: str = None, required: bool = True) -> str:
        """Get input from user with optional default and validation."""
        while True:
            if default:
                value = input(f"{prompt} [{default}]: ").strip()
                if not value:
                    value = default
            else:
                value = input(f"{prompt}: ").strip()
                
            if value or not required:
                return value
            elif required:
                print("This field is required. Please enter a value.")

    def _get_choice(self, prompt: str, choices: List[str], allow_none: bool = False) -> Optional[str]:
        """Get a choice from a list of options."""
        print(f"\n{prompt}")
        for i, choice in enumerate(choices, 1):
            print(f"  {i}. {choice}")
        if allow_none:
            print(f"  {len(choices) + 1}. Skip/None")
            
        while True:
            try:
                choice_num = int(input(f"Enter choice (1-{len(choices) + (1 if allow_none else 0)}): "))
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1]
                elif allow_none and choice_num == len(choices) + 1:
                    return None
                else:
                    print(f"Please enter a number between 1 and {len(choices) + (1 if allow_none else 0)}")
            except ValueError:
                print("Please enter a valid number.")

    def _generate_node_id(self) -> str:
        """Generate a unique node ID."""
        node_id = f"node_{self.next_node_id:03d}"
        self.next_node_id += 1
        return node_id

    def _onboard_mpfs(self):
        """Onboard Mass Production Facilities."""
        print("\n" + "="*50)
        print("STEP 1: Mass Production Facilities (MPFs)")
        print("="*50)
        print("MPFs are large-scale production facilities that can manufacture")
        print("vehicles, ships, and equipment with bulk discounts.")
        
        while True:
            if not self._confirm("\nAdd an MPF? (y/n): "):
                break
                
            name = self._get_input("MPF Location/Name", required=True)
            
            # Create MPF node
            node_id = self._generate_node_id()
            mpf_node = MassProductionFactoryNode(
                node_id=node_id,
                location_name=name,
                unit_size="crate",
                base_type=BaseType.PRODUCTION,
                production_type=ProductionType.MPF
            )
            
            # Set metadata
            mpf_node.metadata.update({
                "facility_type": "MPF",
                "description": "Mass Production Facility"
            })
            
            self.nodes[node_id] = mpf_node
            self.graph.add_node(mpf_node)
            
            print(f"✅ Added MPF: {name} (ID: {node_id})")
            
        if not self.nodes:
            print("⚠️  No MPFs added. You can add them later if needed.")

    def _onboard_refineries(self):
        """Onboard refineries."""
        print("\n" + "="*50)
        print("STEP 2: Refineries")
        print("="*50)
        print("Refineries process raw materials into basic materials (BMats, EMats, etc.)")
        
        while True:
            if not self._confirm("\nAdd a refinery? (y/n): "):
                break
                
            name = self._get_input("Refinery Location/Name", required=True)
            
            # Choose refinery type
            refinery_types = [
                "Basic Materials Refinery",
                "Explosive Materials Refinery", 
                "Fuel Refinery",
                "Other/Custom"
            ]
            refinery_type = self._get_choice("Select refinery type:", refinery_types)
            
            # Create refinery node
            node_id = self._generate_node_id()
            refinery_node = RefineryNode(
                node_id=node_id,
                location_name=name,
                unit_size="crate",
                base_type=BaseType.REFINERY,
                production_type=ProductionType.FACILITY,
                facility_type=FacilityType.REFINERY
            )
            
            # Set metadata
            refinery_node.metadata.update({
                "facility_type": "Refinery",
                "refinery_type": refinery_type,
                "description": f"{refinery_type} at {name}"
            })
            
            self.nodes[node_id] = refinery_node
            self.graph.add_node(refinery_node)
            
            print(f"✅ Added Refinery: {name} ({refinery_type}) (ID: {node_id})")

    def _onboard_factories(self):
        """Onboard factories."""
        print("\n" + "="*50)
        print("STEP 3: Factories")
        print("="*50)
        print("Factories produce weapons, ammunition, and equipment.")
        
        while True:
            if not self._confirm("\nAdd a factory? (y/n): "):
                break
                
            name = self._get_input("Factory Location/Name", required=True)
            
            # Choose factory type
            factory_types = [
                "Small Arms Factory",
                "Heavy Arms Factory", 
                "Ammunition Factory",
                "Utility Factory",
                "Medical Factory",
                "Other/Custom"
            ]
            factory_type = self._get_choice("Select factory type:", factory_types)
            
            # Create factory node
            node_id = self._generate_node_id()
            factory_node = FactoryNode(
                node_id=node_id,
                location_name=name,
                unit_size="crate",
                base_type=BaseType.PRODUCTION,
                production_type=ProductionType.FACTORY
            )
            
            # Set metadata
            factory_node.metadata.update({
                "facility_type": "Factory",
                "factory_type": factory_type,
                "description": f"{factory_type} at {name}"
            })
            
            self.nodes[node_id] = factory_node
            self.graph.add_node(factory_node)
            
            print(f"✅ Added Factory: {name} ({factory_type}) (ID: {node_id})")

    def _onboard_facilities(self):
        """Onboard other facilities (storage, depots, etc.)."""
        print("\n" + "="*50)
        print("STEP 4: Other Facilities")
        print("="*50)
        print("Other facilities include storage depots, seaports, garages, etc.")
        
        while True:
            if not self._confirm("\nAdd a facility? (y/n): "):
                break
                
            name = self._get_input("Facility Location/Name", required=True)
            
            # Choose facility type
            facility_types = [
                "Storage Depot",
                "Seaport",
                "Garage",
                "Shipyard", 
                "Construction Yard",
                "Other/Custom"
            ]
            facility_type = self._get_choice("Select facility type:", facility_types)
            
            # Create facility node
            node_id = self._generate_node_id()
            facility_node = FacilityNode(
                node_id=node_id,
                location_name=name,
                unit_size="crate",
                base_type=BaseType.FACILITY,
                production_type=ProductionType.FACILITY
            )
            
            # Set metadata
            facility_node.metadata.update({
                "facility_type": facility_type,
                "description": f"{facility_type} at {name}"
            })
            
            self.nodes[node_id] = facility_node
            self.graph.add_node(facility_node)
            
            print(f"✅ Added Facility: {name} ({facility_type}) (ID: {node_id})")

    def _configure_connections(self):
        """Configure connections between nodes."""
        print("\n" + "="*50)
        print("STEP 5: Network Connections")
        print("="*50)
        print("Now we'll set up connections between your facilities.")
        print("Connections define how materials flow through your network.")
        
        if len(self.nodes) < 2:
            print("⚠️  You need at least 2 nodes to create connections.")
            return
            
        # Show available nodes
        print("\nAvailable nodes:")
        node_list = list(self.nodes.items())
        for i, (node_id, node) in enumerate(node_list, 1):
            facility_type = node.metadata.get("facility_type", "Unknown")
            print(f"  {i}. {node.location_name} ({facility_type}) [ID: {node_id}]")
        
        while True:
            if not self._confirm("\nAdd a connection? (y/n): "):
                break
                
            # Select source node
            print("\nSelect SOURCE node (where materials come FROM):")
            source_choices = [f"{node.location_name} ({node.metadata.get('facility_type', 'Unknown')})" 
                            for _, node in node_list]
            source_idx = self._get_choice("Source node:", source_choices)
            if source_idx is None:
                continue
            source_node_id, source_node = node_list[source_choices.index(source_idx)]
            
            # Select target node
            print("\nSelect TARGET node (where materials go TO):")
            target_choices = [f"{node.location_name} ({node.metadata.get('facility_type', 'Unknown')})" 
                            for _, node in node_list if node != source_node]
            if not target_choices:
                print("No valid target nodes available.")
                continue
                
            target_idx = self._get_choice("Target node:", target_choices)
            if target_idx is None:
                continue
            
            # Find the actual target node
            target_node = None
            for node_id, node in node_list:
                node_display = f"{node.location_name} ({node.metadata.get('facility_type', 'Unknown')})"
                if node_display == target_idx and node != source_node:
                    target_node_id, target_node = node_id, node
                    break
            
            if not target_node:
                print("Error: Could not find target node.")
                continue
            
            # Configure allowed items (optional)
            allowed_items = []
            if self._confirm("Specify allowed items for this connection? (y/n): "):
                print("Enter allowed items (comma-separated, or press Enter for all items):")
                items_input = input("Items: ").strip()
                if items_input:
                    allowed_items = [item.strip() for item in items_input.split(",")]
            
            # Create the connection
            try:
                self.graph.add_edge(
                    source_node_id, 
                    target_node_id,
                    allowed_items=allowed_items if allowed_items else None
                )
                
                print(f"✅ Added connection: {source_node.location_name} → {target_node.location_name}")
                if allowed_items:
                    print(f"   Allowed items: {', '.join(allowed_items)}")
                    
            except Exception as e:
                print(f"❌ Error adding connection: {e}")

    def _configure_frontline_status(self):
        """Configure frontline status for nodes."""
        print("\n" + "="*50)
        print("STEP 6: Frontline Status (Demo/Testing)")
        print("="*50)
        print("Mark facilities as 'frontline' for demo and testing scenarios.")
        
        if not self.nodes:
            print("No nodes available to mark as frontline.")
            return
            
        print("\nAvailable nodes:")
        node_list = list(self.nodes.items())
        for i, (node_id, node) in enumerate(node_list, 1):
            facility_type = node.metadata.get("facility_type", "Unknown")
            frontline = node.metadata.get("frontline", False)
            status = "🔥 FRONTLINE" if frontline else "🏠 Rear"
            print(f"  {i}. {node.location_name} ({facility_type}) [{status}]")
        
        while True:
            if not self._confirm("\nMark a facility as frontline? (y/n): "):
                break
                
            # Select node to mark as frontline
            choices = [f"{node.location_name} ({node.metadata.get('facility_type', 'Unknown')})" 
                      for _, node in node_list]
            choice = self._get_choice("Select facility to mark as frontline:", choices)
            if choice is None:
                continue
                
            # Find and update the node
            for node_id, node in node_list:
                node_display = f"{node.location_name} ({node.metadata.get('facility_type', 'Unknown')})"
                if node_display == choice:
                    node.metadata["frontline"] = True
                    print(f"✅ Marked {node.location_name} as frontline")
                    break

    def _show_network_summary(self):
        """Display a summary of the configured network."""
        print("\n" + "="*60)
        print("NETWORK SUMMARY")
        print("="*60)
        
        if not self.nodes:
            print("No nodes configured.")
            return
            
        print(f"\nTotal nodes: {len(self.nodes)}")
        print(f"Total connections: {len(self.graph.edges)}")
        
        # Group nodes by type
        node_types = {}
        frontline_nodes = []
        
        for node_id, node in self.nodes.items():
            facility_type = node.metadata.get("facility_type", "Unknown")
            if facility_type not in node_types:
                node_types[facility_type] = []
            node_types[facility_type].append(node)
            
            if node.metadata.get("frontline", False):
                frontline_nodes.append(node)
        
        # Display by type
        print("\nNodes by type:")
        for facility_type, nodes in node_types.items():
            print(f"\n  {facility_type}:")
            for node in nodes:
                frontline_marker = " 🔥" if node.metadata.get("frontline", False) else ""
                print(f"    - {node.location_name}{frontline_marker}")
        
        # Display connections
        if self.graph.edges:
            print("\nConnections:")
            for edge in self.graph.edges:
                source_name = edge.source.location_name
                target_name = edge.target.location_name
                allowed_items = edge.allowed_items
                if allowed_items:
                    items_str = f" (items: {', '.join(allowed_items)})"
                else:
                    items_str = " (all items)"
                print(f"    {source_name} → {target_name}{items_str}")
        
        # Display frontline facilities
        if frontline_nodes:
            print(f"\nFrontline facilities ({len(frontline_nodes)}):")
            for node in frontline_nodes:
                facility_type = node.metadata.get("facility_type", "Unknown")
                print(f"    🔥 {node.location_name} ({facility_type})")

    def _save_network(self):
        """Save the network to a file."""
        print("\n" + "="*50)
        print("SAVE NETWORK")
        print("="*50)
        
        if not self._confirm("Save network to file? (y/n): "):
            print("Network not saved.")
            return
            
        # Get filename
        default_filename = "foxhole_logistics_network"
        filename = self._get_input("Filename (without extension)", default=default_filename)
        
        # Choose format
        formats = ["YAML", "JSON"]
        format_choice = self._get_choice("Select format:", formats)
        
        if format_choice == "YAML":
            filepath = f"{filename}.yaml"
            self._save_yaml(filepath)
        else:
            filepath = f"{filename}.json"
            self._save_json(filepath)
            
        print(f"✅ Network saved to: {filepath}")

    def _serialize_network(self) -> Dict[str, Any]:
        """Serialize the network to a dictionary."""
        network_data = {
            "metadata": {
                "version": "1.0",
                "tool": "Foxhole Automated Quartermaster - Network Onboarding",
                "description": "Foxhole logistics network configuration"
            },
            "nodes": {},
            "edges": []
        }
        
        # Serialize nodes
        for node_id, node in self.nodes.items():
            node_data = {
                "id": node_id,
                "location_name": node.location_name,
                "unit_size": node.unit_size,
                "base_type": node.base_type.value if hasattr(node.base_type, 'value') else str(node.base_type),
                "metadata": node.metadata.copy(),
                "inventory": node.inventory.copy(),
                "delta": node.delta.copy(),
                "status": node.status
            }
            
            # Add production-specific data
            if hasattr(node, 'production_type') and node.production_type:
                node_data["production_type"] = node.production_type.value if hasattr(node.production_type, 'value') else str(node.production_type)
            if hasattr(node, 'facility_type') and node.facility_type:
                node_data["facility_type"] = node.facility_type.value if hasattr(node.facility_type, 'value') else str(node.facility_type)
            if hasattr(node, 'process_type') and node.process_type:
                node_data["process_type"] = node.process_type.value if hasattr(node.process_type, 'value') else str(node.process_type)
            
            network_data["nodes"][node_id] = node_data
        
        # Serialize edges
        for edge in self.graph.edges:
            edge_data = {
                "source": edge.source.node_id,
                "target": edge.target.node_id,
                "allowed_items": edge.allowed_items.copy() if edge.allowed_items else None,
                "production_process": edge.production_process,
                "user_config": edge.user_config.copy() if edge.user_config else None
            }
            network_data["edges"].append(edge_data)
        
        return network_data

    def _save_yaml(self, filepath: str):
        """Save network as YAML file."""
        network_data = self._serialize_network()
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(network_data, f, default_flow_style=False, indent=2, sort_keys=False)

    def _save_json(self, filepath: str):
        """Save network as JSON file."""
        network_data = self._serialize_network()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(network_data, f, indent=2, ensure_ascii=False)

    def load_network(self, filepath: str) -> bool:
        """Load a network from file."""
        try:
            # Determine format from extension
            if filepath.endswith('.yaml') or filepath.endswith('.yml'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    network_data = yaml.safe_load(f)
            elif filepath.endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    network_data = json.load(f)
            else:
                print(f"❌ Unsupported file format. Use .yaml, .yml, or .json")
                return False
                
            return self._deserialize_network(network_data)
            
        except FileNotFoundError:
            print(f"❌ File not found: {filepath}")
            return False
        except Exception as e:
            print(f"❌ Error loading network: {e}")
            return False

    def _deserialize_network(self, network_data: Dict[str, Any]) -> bool:
        """Deserialize network data into graph objects."""
        try:
            # Clear existing data
            self.graph = InventoryGraph()
            self.nodes.clear()
            
            # Load nodes
            nodes_data = network_data.get("nodes", {})
            for node_id, node_data in nodes_data.items():
                node = self._create_node_from_data(node_id, node_data)
                if node:
                    self.nodes[node_id] = node
                    self.graph.add_node(node)
            
            # Load edges
            edges_data = network_data.get("edges", [])
            for edge_data in edges_data:
                source_id = edge_data.get("source")
                target_id = edge_data.get("target")
                if source_id in self.nodes and target_id in self.nodes:
                    self.graph.add_edge(
                        source_id,
                        target_id,
                        allowed_items=edge_data.get("allowed_items"),
                        production_process=edge_data.get("production_process"),
                        user_config=edge_data.get("user_config")
                    )
            
            # Update next_node_id
            if self.nodes:
                max_id = max(int(node_id.split('_')[1]) for node_id in self.nodes.keys() if node_id.startswith('node_'))
                self.next_node_id = max_id + 1
            
            return True
            
        except Exception as e:
            print(f"❌ Error deserializing network: {e}")
            return False

    def _create_node_from_data(self, node_id: str, node_data: Dict[str, Any]) -> Optional[InventoryNode]:
        """Create a node object from serialized data."""
        try:
            base_type_str = node_data.get("base_type", "ITEM_NODE")
            base_type = BaseType(base_type_str) if hasattr(BaseType, base_type_str) else BaseType.ITEM_NODE
            
            location_name = node_data.get("location_name", "Unknown")
            unit_size = node_data.get("unit_size", "crate")
            
            # Determine node class based on metadata and types
            facility_type_meta = node_data.get("metadata", {}).get("facility_type", "")
            production_type_str = node_data.get("production_type")
            
            # Create appropriate node type
            if facility_type_meta == "MPF" or production_type_str == "MassProductionFactory":
                node = MassProductionFactoryNode(
                    node_id=node_id,
                    location_name=location_name,
                    unit_size=unit_size,
                    base_type=base_type,
                    production_type=ProductionType.MPF
                )
            elif facility_type_meta == "Factory" or production_type_str == "Factory":
                node = FactoryNode(
                    node_id=node_id,
                    location_name=location_name,
                    unit_size=unit_size,
                    base_type=base_type,
                    production_type=ProductionType.FACTORY
                )
            elif facility_type_meta == "Refinery" or base_type == BaseType.REFINERY:
                node = RefineryNode(
                    node_id=node_id,
                    location_name=location_name,
                    unit_size=unit_size,
                    base_type=BaseType.REFINERY,
                    production_type=ProductionType.FACILITY,
                    facility_type=FacilityType.REFINERY
                )
            elif base_type == BaseType.FACILITY or facility_type_meta in ["Storage Depot", "Seaport", "Garage", "Shipyard", "Construction Yard"]:
                node = FacilityNode(
                    node_id=node_id,
                    location_name=location_name,
                    unit_size=unit_size,
                    base_type=base_type,
                    production_type=ProductionType.FACILITY
                )
            else:
                # Default to basic InventoryNode
                node = InventoryNode(
                    node_id=node_id,
                    location_name=location_name,
                    unit_size=unit_size,
                    base_type=base_type
                )
            
            # Restore node data
            node.metadata = node_data.get("metadata", {}).copy()
            node.inventory = node_data.get("inventory", {}).copy()
            node.delta = node_data.get("delta", {}).copy()
            node.status = node_data.get("status", "unknown")
            
            return node
            
        except Exception as e:
            print(f"❌ Error creating node {node_id}: {e}")
            return None

    def print_network_status(self):
        """Print the current network status for debugging."""
        print("\n" + "="*60)
        print("NETWORK STATUS")
        print("="*60)
        
        if not self.nodes:
            print("No network loaded.")
            return
            
        print(f"Nodes: {len(self.nodes)}")
        print(f"Edges: {len(self.graph.edges)}")
        
        # Print all nodes
        print("\nNodes:")
        for node_id, node in self.nodes.items():
            facility_type = node.metadata.get("facility_type", "Unknown")
            frontline = " 🔥" if node.metadata.get("frontline", False) else ""
            print(f"  {node_id}: {node.location_name} ({facility_type}){frontline}")
        
        # Print all edges
        print("\nEdges:")
        for edge in self.graph.edges:
            print(f"  {edge.source.node_id} → {edge.target.node_id}")
            if edge.allowed_items:
                print(f"    Items: {', '.join(edge.allowed_items)}")


def main():
    """Main entry point for the CLI tool."""
    parser = argparse.ArgumentParser(
        description="Foxhole Automated Quartermaster - Network Onboarding CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python onboard_network.py                    # Interactive onboarding
  python onboard_network.py --load network.yaml  # Load and display network
  python onboard_network.py --status network.yaml # Show network status
        """
    )
    
    parser.add_argument(
        "--load", 
        metavar="FILE",
        help="Load an existing network from file"
    )
    
    parser.add_argument(
        "--status",
        metavar="FILE", 
        help="Load network and display status"
    )
    
    args = parser.parse_args()
    
    cli = NetworkOnboardingCLI()
    
    if args.load:
        print(f"Loading network from: {args.load}")
        if cli.load_network(args.load):
            print("✅ Network loaded successfully!")
            cli.print_network_status()
        else:
            sys.exit(1)
            
    elif args.status:
        print(f"Loading network status from: {args.status}")
        if cli.load_network(args.status):
            cli.print_network_status()
        else:
            sys.exit(1)
            
    else:
        # Interactive onboarding
        cli.run()


if __name__ == "__main__":
    main()