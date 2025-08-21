from typing import Dict, Any, Optional
from services.inventory.production_nodes import BaseNode, BaseType
from services.inventory.order import Order

class ResourceNode(BaseNode):
    """
    Node for managing resource orders and assignments in the logistics network.
    Maintains worker assignments and rolls up totals for status reporting.
    """
    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate"):
        super().__init__(node_id, location_name, unit_size, BaseType.RESOURCE)
        self.worker_assignments: Dict[str, str] = {}  # user_id -> loop/task
        self.total_salvage_needed: int = 0

    def add_order(self, item: str, quantity: int, target_node: 'InventoryNode', status: str = "pending", salvage_needed: Optional[int] = None, **kwargs) -> None:
        order = Order(
            item, quantity, self, target_node,
            status=status, order_type="transport",
            blocking_resources=kwargs.get("blocking_resources", [])
        )
        order.salvage_needed = salvage_needed if salvage_needed is not None else 0
        # Attach order to edge
        for edge in self.edges:
            if edge.target == target_node:
                edge.add_order(order)
                break
        self._recalculate_totals()

    def remove_order(self, item: str, target_node: 'InventoryNode') -> bool:
        for edge in self.edges:
            if edge.target == target_node:
                orders = edge.get_orders()
                for order in orders:
                    if order.item == item:
                        edge.remove_order(order)
                        self._recalculate_totals()
                        return True
        return False

    def update_order(self, item: str, target_node: 'InventoryNode', **kwargs) -> bool:
        for edge in self.edges:
            if edge.target == target_node:
                orders = edge.get_orders()
                for order in orders:
                    if order.item == item:
                        for k, v in kwargs.items():
                            setattr(order, k, v)
                        self._recalculate_totals()
                        return True
        return False

    def assign_worker(self, user_id: str, loop: str) -> None:
        self.worker_assignments[user_id] = loop

    def unassign_worker(self, user_id: str) -> None:
        if user_id in self.worker_assignments:
            del self.worker_assignments[user_id]

    def _recalculate_totals(self) -> None:
        total = 0
        for edge in self.edges:
            for order in edge.get_orders():
                if hasattr(order, 'salvage_needed'):
                    total += getattr(order, 'salvage_needed', 0)
        self.total_salvage_needed = total

    def get_status_board_data(self) -> Dict[str, Any]:
        orders = []
        for edge in self.edges:
            for order in edge.get_orders():
                order_data = {
                    "item": order.item,
                    "quantity": order.quantity,
                    "status": order.status,
                    "salvage_needed": getattr(order, 'salvage_needed', 0)
                }
                orders.append(order_data)
        return {
            "node_id": self.node_id,
            "location_name": self.location_name,
            "orders": orders,
            "total_salvage_needed": self.total_salvage_needed,
            "worker_assignments": self.worker_assignments,
            "status": self.status
        }

    def __repr__(self):
        order_count = sum(len(edge.get_orders()) for edge in self.edges)
        return (f"<ResourceNode id={self.node_id} name={self.location_name} "
                f"orders={order_count} salvage={self.total_salvage_needed} workers={len(self.worker_assignments)}>")
