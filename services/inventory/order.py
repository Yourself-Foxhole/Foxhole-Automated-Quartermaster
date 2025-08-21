from typing import Optional
from services.inventory.inventory_graph import InventoryNode

class Order:
    def __init__(self, item: str, quantity: int, source: InventoryNode, target: InventoryNode, status: str = "pending", created_at: Optional[float] = None, order_type: str = "production", blocking_resources: Optional[list] = None):
        self.item = item
        self.quantity = quantity
        self.source = source
        self.target = target
        self.status = status  # e.g., 'pending', 'in_transit', 'fulfilled', 'cancelled', 'blocked', 'queued'
        self.created_at = created_at
        self.updated_at = created_at
        self.type = order_type  # 'production', 'transport', 'request', etc.
        self.blocking_resources = blocking_resources if blocking_resources is not None else []

    def update_status(self, new_status: str, timestamp: Optional[float] = None):
        self.status = new_status
        if timestamp:
            self.updated_at = timestamp

    def __repr__(self):
        return f"<Order {self.item} x{self.quantity} {self.source.node_id}->{self.target.node_id} type={self.type} status={self.status} blocked={self.blocking_resources}>"
