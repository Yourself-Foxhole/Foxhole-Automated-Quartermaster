from typing import Dict, Any, List
from enum import Enum

class BaseType(Enum):
    RESOURCE = "Resource"
    REFINERY = "CrudeOil"
    PRODUCTION = "Production"
    CRATE_NODE = "CrateNode"
    ITEM_NODE = "ItemNode"
    FACILITY = "Facility"

class BaseNode:
    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate", base_type: BaseType = BaseType.ITEM_NODE):
        self.node_id = node_id
        self.location_name = location_name
        self.unit_size = unit_size
        self.base_type = base_type
        self.inventory: Dict[str, int] = {}
        self.delta: Dict[str, int] = {}
        self.status: str = "unknown"
        self.metadata: Dict[str, Any] = {}
        self.edges: List[Any] = []  # List of InventoryEdge objects
        self.status_table: Dict[str, Dict[str, int]] = {}

    def add_edge(self, edge: Any):
        self.edges.append(edge)

    def compute_delta_from_orders(self):
        total_orders: Dict[str, int] = {}
        for edge in self.edges:
            if hasattr(edge, 'get_orders'):
                for order in edge.get_orders():
                    item = order.item
                    quantity = order.quantity
                    total_orders[item] = total_orders.get(item, 0) + quantity
        self.delta = total_orders

