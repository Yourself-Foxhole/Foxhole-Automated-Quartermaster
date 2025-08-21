from typing import Dict, List, Optional, Any
from services.inventory.production_nodes import (
    BaseType, BaseNode
)
from services.FoxholeDataObjects.processes import ProductionType, FacilityType, ProcessType, PRODUCTION_PROCESS_MAP
from services.inventory.order import Order

class InventoryNode(BaseNode):
    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate", base_type: BaseType = BaseType.ITEM_NODE):
        super().__init__(node_id, location_name, unit_size, base_type)
        self.inventory: Dict[str, int] = {}  # item_name -> quantity
        self.delta: Dict[str, int] = {}      # item_name -> needed quantity
        self.status: str = "unknown"         # e.g., 'ok', 'low', 'critical', etc.
        self.metadata: Dict[str, Any] = {}   # for extensibility
        self.edges: List['InventoryEdge'] = []
        self.status_table: Dict[str, Dict[str, int]] = {}  # item_name -> status dict

    def update_inventory(self, inventory_update: Dict[str, int]):
        self.inventory.update(inventory_update)

    def set_delta(self, delta_update: Dict[str, int]):
        self.delta = delta_update

    def set_status(self, status: str):
        self.status = status

    def add_edge(self, edge: 'InventoryEdge'):
        self.edges.append(edge)

    def update_status_table(self, item: str, orders: int = 0, in_transit: int = 0, inventory: int = 0, outbound_orders: int = 0, outbound_in_transit: int = 0):
        if item not in self.status_table:
            self.status_table[item] = {"orders": 0, "in_transit": 0, "inventory": 0, "outbound_orders": 0, "outbound_in_transit": 0}
        if orders is not None:
            self.status_table[item]["orders"] = orders
        if in_transit is not None:
            self.status_table[item]["in_transit"] = in_transit
        if inventory is not None:
            self.status_table[item]["inventory"] = inventory
        if outbound_orders is not None:
            self.status_table[item]["outbound_orders"] = outbound_orders
        if outbound_in_transit is not None:
            self.status_table[item]["outbound_in_transit"] = outbound_in_transit

    def get_status_table(self) -> Dict[str, Dict[str, int]]:
        return self.status_table

    def print_status_table(self):
        print(f"Status Table for {self.location_name} ({self.node_id}):")
        if not self.status_table:
            print("  No status data.")
            return
        for item, status in self.status_table.items():
            print(f"  {item}: orders={status['orders']}, in-transit={status['in_transit']}, inventory={status['inventory']}, outbound-orders={status['outbound_orders']}, outbound-in-transit={status['outbound_in_transit']}")


class InventoryEdge:
    def __init__(self, source: 'InventoryNode', target: 'InventoryNode',
                 allowed_items: Optional[List[str]] = None,
                 production_process: Optional[str] = None,
                 user_config: Optional[Dict[str, Any]] = None):
        self.source = source
        self.target = target
        self.allowed_items = allowed_items or []
        self.production_process = production_process
        self.user_config = user_config or {}
        self.orders: List[Order] = []  # List of Order objects attached to this edge

    def add_order(self, order: Order):
        self.orders.append(order)

    def remove_order(self, order: Order):
        if order in self.orders:
            self.orders.remove(order)

    def get_orders(self) -> List[Order]:
        return self.orders

class InventoryGraph:
    def __init__(self):
        self.nodes: Dict[str, InventoryNode] = {}
        self.edges: List[InventoryEdge] = []

    def add_node(self, node: InventoryNode):
        self.nodes[node.node_id] = node

    def add_edge(self, source_id: str, target_id: str,
                 allowed_items: Optional[List[str]] = None,
                 production_process: Optional[str] = None,
                 user_config: Optional[Dict[str, Any]] = None):
        source = self.nodes[source_id]
        target = self.nodes[target_id]
        edge = InventoryEdge(source, target, allowed_items, production_process, user_config)
        self.edges.append(edge)
        source.add_edge(edge)

    def update_node_from_parsed_object(self, node_id: str, parsed_obj: Dict[str, Any]):
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        node.update_inventory(parsed_obj.get("inventory", {}))
        node.set_delta(parsed_obj.get("delta", {}))
        node.set_status(parsed_obj.get("status", "unknown"))
        node.metadata.update(parsed_obj.get("metadata", {}))

    def get_node(self, node_id: str) -> Optional[InventoryNode]:
        return self.nodes.get(node_id)

    def get_edges(self) -> List[InventoryEdge]:
        return self.edges

    def create_order(self, source_id: str, target_id: str, item: str, quantity: int, status: str = "pending", created_at: Optional[float] = None):
        """
        Create an Order object and attach it to the edge between source and target nodes.
        """
        source = self.nodes[source_id]
        target = self.nodes[target_id]
        # Find the edge
        edge = next((e for e in self.edges if e.source == source and e.target == target), None)
        if not edge:
            raise ValueError(f"No edge found between {source_id} and {target_id}")
        from services.inventory.order import Order
        order = Order(item, quantity, source, target, status, created_at)
        edge.add_order(order)
        return order

    def get_all_orders(self) -> List['Order']:
        """
        Return a list of all Order objects in the graph.
        """
        orders = []
        for edge in self.edges:
            orders.extend(edge.get_orders())
        return orders

    def find_orders(self, source_id: Optional[str] = None, target_id: Optional[str] = None, item: Optional[str] = None, status: Optional[str] = None) -> List['Order']:
        """
        Find orders by source, target, item, or status.
        """
        results = []
        for order in self.get_all_orders():
            if source_id and order.source.node_id != source_id:
                continue
            if target_id and order.target.node_id != target_id:
                continue
            if item and order.item != item:
                continue
            if status and order.status != status:
                continue
            results.append(order)
        return results

    def print_status(self):
        print("Inventory Graph Status:")
        for node_id, node in self.nodes.items():
            print(f"Node {node_id} ({node.location_name}):")
            print(f"  Unit Size: {node.unit_size}")
            print(f"  Status: {node.status}")
            print(f"  Inventory: {node.inventory}")
            print(f"  Delta: {node.delta}")
            if node.metadata:
                print(f"  Metadata: {node.metadata}")
            for edge in node.edges:
                print(f"    -> {edge.target.node_id} ({edge.target.location_name}) | Allowed: {edge.allowed_items} | Production: {edge.production_process} | User Config: {edge.user_config}")
        print("")


def integration_example_basic_graph():
    """Create a simple graph with two nodes and an edge, then update inventory."""
    graph = InventoryGraph()
    node1 = InventoryNode("n1", "Factory A")
    node2 = InventoryNode("n2", "Depot B")
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge("n1", "n2", allowed_items=["rifle", "ammo"])
    graph.update_node_from_parsed_object("n1", {"inventory": {"rifle": 10}, "delta": {"rifle": 5}, "status": "ok"})
    return graph


def integration_example_production_chain():
    """Create a production chain: Resource Node -> Factory -> Depot, with deltas and production process."""
    graph = InventoryGraph()
    resource = InventoryNode("r1", "Salvage Field", unit_size="item")
    factory = InventoryNode("f1", "Frontline Factory")
    depot = InventoryNode("d1", "Frontline Depot")
    graph.add_node(resource)
    graph.add_node(factory)
    graph.add_node(depot)
    # Resource to Factory (produces bmats)
    graph.add_edge("r1", "f1", allowed_items=["salvage"], production_process="refine_salvage_to_bmats")
    # Factory to Depot (produces rifles)
    graph.add_edge("f1", "d1", allowed_items=["rifle"], production_process="assemble_rifle")
    # Set inventory and deltas
    graph.update_node_from_parsed_object("r1", {"inventory": {"salvage": 1000}, "delta": {"salvage": 0}, "status": "ok"})
    graph.update_node_from_parsed_object("f1", {"inventory": {"bmats": 200}, "delta": {"bmats": 100, "rifle": 50}, "status": "low"})
    graph.update_node_from_parsed_object("d1", {"inventory": {"rifle": 10}, "delta": {"rifle": 40}, "status": "critical"})
    return graph


def integration_example_with_metadata():
    """Create a node with custom metadata and a user-configured edge."""
    graph = InventoryGraph()
    node = InventoryNode("n3", "Special Facility", unit_size="crate")
    node.metadata = {"facility_type": "advanced", "hex": "Deadlands"}
    graph.add_node(node)
    # Add a self-loop edge with user config
    graph.add_edge("n3", "n3", allowed_items=["prototype"], user_config={"priority": "high", "notes": "Test edge"})
    return graph


if __name__ == "__main__":
    # Example usage (to be removed in production):
    graph = InventoryGraph()
    node1 = InventoryNode("n1", "Factory A")
    node2 = InventoryNode("n2", "Depot B")
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge("n1", "n2", allowed_items=["rifle", "ammo"])
    graph.update_node_from_parsed_object("n1", {"inventory": {"rifle": 10}, "delta": {"rifle": 5}, "status": "ok"})
    graph.print_status()
