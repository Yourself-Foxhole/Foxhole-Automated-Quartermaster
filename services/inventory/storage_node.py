from typing import Dict, Any, Optional
from services.inventory.production_nodes import BaseNode, BaseType

class StorageNode(BaseNode):
    """
    Represents a node in the logistics graph for different types of stockpiles.
    Types:
        - 'item': Stores individual items, can unpack crates, unlimited quantity up to 32,000 per item.
        - 'crate': Stores crates, typically depots, seaports, or ships.
        - 'shippable': Stores shippables (containers, vehicles), e.g., container yards, rail yards, ships.
    """
    STOCKPILE_LIMIT = 32000
    VALID_TYPES = {"item", "crate", "shippable"}

    def __init__(self, node_type: str, node_id: str, location_name: str, unit_size: str = "crate", contents: Optional[Dict[str, int]] = None):
        if node_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid node_type: {node_type}. Must be one of {self.VALID_TYPES}")
        # Map node_type to BaseType
        if node_type == "item":
            base_type = BaseType.ITEM_NODE
        elif node_type == "crate":
            base_type = BaseType.CRATE_NODE
        else:
            base_type = BaseType.PRODUCTION  # Default for shippable
        super().__init__(node_id, location_name, unit_size, base_type)
        self.type = node_type
        if contents:
            self.inventory = contents.copy()

    def add(self, item: str, quantity: int) -> None:
        """Add items/crates/shippables to the node, enforcing limits for item nodes."""
        if self.type == "item":
            current = self.inventory.get(item, 0)
            new_total = min(current + quantity, self.STOCKPILE_LIMIT)
            self.inventory[item] = new_total
        else:
            self.inventory[item] = self.inventory.get(item, 0) + quantity

    def remove(self, item: str, quantity: int) -> int:
        """Remove items/crates/shippables. Returns actual quantity removed."""
        current = self.inventory.get(item, 0)
        removed = min(current, quantity)
        if removed > 0:
            self.inventory[item] = current - removed
            if self.inventory[item] == 0:
                del self.inventory[item]
        return removed

    def unpack_crate(self, crate: str, item: str, quantity: int) -> bool:
        """
        Unpack crates into items. Only allowed for item nodes.
        Returns True if successful, False otherwise.
        """
        if self.type != "item":
            return False
        crate_count = self.inventory.get(crate, 0)
        if crate_count < quantity:
            return False
        self.remove(crate, quantity)
        self.add(item, quantity)
        return True

    def __repr__(self):
        return f"<StorageNode id={self.node_id} name={self.location_name} type={self.type} inventory={self.inventory}>"
