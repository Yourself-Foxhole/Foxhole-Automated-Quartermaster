from typing import Dict, List, Any, Optional
from services.inventory.production_nodes import BaseNode, BaseType

class ResourceNode(BaseNode):
    """
    Node for managing resource orders and assignments in the logistics network.
    Maintains an order table, worker assignments, and rolls up totals for status reporting.
    """
    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate"):
        super().__init__(node_id, location_name, unit_size, BaseType.RESOURCE)
        self.order_table: List[Dict[str, Any]] = []  # Each order: {item, quantity, status, salvage_needed, ...}
        self.worker_assignments: Dict[str, str] = {}  # user_id -> loop/task
        self.total_salvage_needed: int = 0

    def add_order(self, item: str, quantity: int, status: str = "pending", salvage_needed: Optional[int] = None, **kwargs) -> None:
        order = {
            "item": item,
            "quantity": quantity,
            "status": status,
            "salvage_needed": salvage_needed if salvage_needed is not None else 0,
            **kwargs
        }
        self.order_table.append(order)
        self._recalculate_totals()

    def remove_order(self, index: int) -> bool:
        if 0 <= index < len(self.order_table):
            self.order_table.pop(index)
            self._recalculate_totals()
            return True
        return False

    def update_order(self, index: int, **kwargs) -> bool:
        if 0 <= index < len(self.order_table):
            self.order_table[index].update(kwargs)
            self._recalculate_totals()
            return True
        return False

    def assign_worker(self, user_id: str, loop: str) -> None:
        self.worker_assignments[user_id] = loop

    def unassign_worker(self, user_id: str) -> None:
        if user_id in self.worker_assignments:
            del self.worker_assignments[user_id]

    def _recalculate_totals(self) -> None:
        self.total_salvage_needed = sum(order.get("salvage_needed", 0) for order in self.order_table)

    def get_status_board_data(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "location_name": self.location_name,
            "orders": self.order_table,
            "total_salvage_needed": self.total_salvage_needed,
            "worker_assignments": self.worker_assignments,
            "status": self.status
        }

    def __repr__(self):
        return (f"<ResourceNode id={self.node_id} name={self.location_name} "
                f"orders={len(self.order_table)} salvage={self.total_salvage_needed} workers={len(self.worker_assignments)}>")
