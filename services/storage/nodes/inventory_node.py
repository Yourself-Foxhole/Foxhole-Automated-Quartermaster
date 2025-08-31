"""
PersistentInventoryNode - Logistics nodes with inventory tracking.

Specialized persistent node for inventory management with capacity limits,
priority weights, and real-time stock tracking for Foxhole logistics.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from persistent.list import PersistentList
from persistent.mapping import PersistentMapping

from .base_node import PersistentBaseNode

logger = logging.getLogger(__name__)


class PersistentInventoryNode(PersistentBaseNode):
    """
    Persistent node for inventory management and logistics tracking.

    Extends PersistentBaseNode with inventory-specific functionality including
    stock tracking, capacity management, priority weights, and logistics coordination.
    """

    def __init__(
        self,
        node_id: Optional[str] = None,
        name: str = "",
        location: str = "",
        **kwargs,
    ):
        """
        Initialize inventory node.

        Args:
            node_id: Unique identifier for the node
            name: Human-readable name for the node
            location: Physical location or region identifier
            **kwargs: Additional attributes
        """
        super().__init__(node_id=node_id, name=name, node_type="inventory", **kwargs)

        # Location and facility information
        self.location = location
        self.facility_type = kwargs.get("facility_type", "storage")
        self.region = kwargs.get("region", "")
        self.coordinates = PersistentMapping(kwargs.get("coordinates", {}))

        # Inventory tracking
        self.current_inventory = PersistentMapping()
        self.reserved_inventory = PersistentMapping()
        self.incoming_shipments = PersistentList()
        self.outgoing_shipments = PersistentList()

        # Capacity management
        self.max_capacity = kwargs.get("max_capacity", 1000)
        self.capacity_by_type = PersistentMapping(kwargs.get("capacity_by_type", {}))
        self.weight_limit = kwargs.get("weight_limit", None)
        self.volume_limit = kwargs.get("volume_limit", None)

        # Priority and logistics
        self.priority_weight = kwargs.get("priority_weight", 1.0)
        self.supply_priority = kwargs.get("supply_priority", "normal")
        self.logistics_role = kwargs.get("logistics_role", "hub")

        # Access and security
        self.access_level = kwargs.get("access_level", "public")
        self.authorized_users = PersistentList(kwargs.get("authorized_users", []))
        self.faction = kwargs.get("faction", "neutral")

        # Operational status
        self.is_operational = kwargs.get("is_operational", True)
        self.operational_hours = PersistentMapping(kwargs.get("operational_hours", {}))
        self.maintenance_schedule = PersistentList()

        logger.debug(f"Created inventory node: {self.node_id} at {location}")

    def add_inventory(
        self, item_name: str, quantity: float, quality: str = "standard"
    ) -> bool:
        """
        Add inventory to the node.

        Args:
            item_name: Name of the item
            quantity: Quantity to add
            quality: Quality level of the item

        Returns:
            True if inventory was added successfully
        """
        if not self._can_accommodate(item_name, quantity):
            logger.warning(
                f"Cannot accommodate {quantity} of {item_name} at {self.name}"
            )
            return False

        # Create item key with quality
        item_key = f"{item_name}:{quality}"

        # Add to current inventory
        current = self.current_inventory.get(item_key, 0.0)
        self.current_inventory[item_key] = current + quantity

        self.update_modified_time()
        logger.debug(f"Added {quantity} {item_name} ({quality}) to {self.name}")
        return True

    def remove_inventory(
        self, item_name: str, quantity: float, quality: str = "standard"
    ) -> bool:
        """
        Remove inventory from the node.

        Args:
            item_name: Name of the item
            quantity: Quantity to remove
            quality: Quality level of the item

        Returns:
            True if inventory was removed successfully
        """
        item_key = f"{item_name}:{quality}"
        current = self.current_inventory.get(item_key, 0.0)

        if current < quantity:
            logger.warning(
                f"Insufficient {item_name} ({quality}) at {self.name}: {current} < {quantity}"
            )
            return False

        self.current_inventory[item_key] = current - quantity

        # Remove entry if quantity reaches zero
        if self.current_inventory[item_key] <= 0:
            del self.current_inventory[item_key]

        self.update_modified_time()
        logger.debug(f"Removed {quantity} {item_name} ({quality}) from {self.name}")
        return True

    def reserve_inventory(
        self,
        item_name: str,
        quantity: float,
        reservation_id: str,
        quality: str = "standard",
    ) -> bool:
        """
        Reserve inventory for future use.

        Args:
            item_name: Name of the item
            quantity: Quantity to reserve
            reservation_id: Unique ID for the reservation
            quality: Quality level of the item

        Returns:
            True if reservation was successful
        """
        item_key = f"{item_name}:{quality}"
        available = self.get_available_inventory(item_name, quality)

        if available < quantity:
            logger.warning(
                f"Insufficient available {item_name} ({quality}) for reservation: {available} < {quantity}"
            )
            return False

        # Track reservation
        if item_key not in self.reserved_inventory:
            self.reserved_inventory[item_key] = PersistentMapping()

        self.reserved_inventory[item_key][reservation_id] = quantity
        self.update_modified_time()

        logger.debug(
            f"Reserved {quantity} {item_name} ({quality}) with ID {reservation_id}"
        )
        return True

    def release_reservation(
        self, item_name: str, reservation_id: str, quality: str = "standard"
    ) -> bool:
        """
        Release a reservation.

        Args:
            item_name: Name of the item
            reservation_id: Unique ID for the reservation
            quality: Quality level of the item

        Returns:
            True if reservation was released
        """
        item_key = f"{item_name}:{quality}"

        if item_key not in self.reserved_inventory:
            return False

        if reservation_id not in self.reserved_inventory[item_key]:
            return False

        del self.reserved_inventory[item_key][reservation_id]

        # Clean up empty reservation containers
        if not self.reserved_inventory[item_key]:
            del self.reserved_inventory[item_key]

        self.update_modified_time()
        logger.debug(
            f"Released reservation {reservation_id} for {item_name} ({quality})"
        )
        return True

    def get_current_inventory(
        self, item_name: Optional[str] = None, quality: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get current inventory levels.

        Args:
            item_name: Optional filter by item name
            quality: Optional filter by quality

        Returns:
            Dictionary of item quantities
        """
        if item_name and quality:
            item_key = f"{item_name}:{quality}"
            return {item_key: self.current_inventory.get(item_key, 0.0)}
        elif item_name:
            return {
                k: v
                for k, v in self.current_inventory.items()
                if k.startswith(f"{item_name}:")
            }
        else:
            return dict(self.current_inventory)

    def get_available_inventory(
        self, item_name: str, quality: str = "standard"
    ) -> float:
        """
        Get available (non-reserved) inventory for an item.

        Args:
            item_name: Name of the item
            quality: Quality level of the item

        Returns:
            Available quantity
        """
        item_key = f"{item_name}:{quality}"
        current = self.current_inventory.get(item_key, 0.0)

        reserved = 0.0
        if item_key in self.reserved_inventory:
            reserved = sum(self.reserved_inventory[item_key].values())

        return max(0.0, current - reserved)

    def get_reserved_inventory(
        self, item_name: Optional[str] = None, quality: Optional[str] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Get reserved inventory information.

        Args:
            item_name: Optional filter by item name
            quality: Optional filter by quality

        Returns:
            Dictionary of reservations by item and reservation ID
        """
        if item_name and quality:
            item_key = f"{item_name}:{quality}"
            return {item_key: dict(self.reserved_inventory.get(item_key, {}))}
        elif item_name:
            return {
                k: dict(v)
                for k, v in self.reserved_inventory.items()
                if k.startswith(f"{item_name}:")
            }
        else:
            return {k: dict(v) for k, v in self.reserved_inventory.items()}

    def _can_accommodate(self, item_name: str, quantity: float) -> bool:
        """
        Check if the node can accommodate additional inventory.

        Args:
            item_name: Name of the item
            quantity: Quantity to check

        Returns:
            True if can accommodate
        """
        # Check general capacity
        current_total = sum(self.current_inventory.values())
        if current_total + quantity > self.max_capacity:
            return False

        # Check item-specific capacity
        if item_name in self.capacity_by_type:
            current_item = sum(
                v
                for k, v in self.current_inventory.items()
                if k.startswith(f"{item_name}:")
            )
            if current_item + quantity > self.capacity_by_type[item_name]:
                return False

        return True

    def add_incoming_shipment(self, shipment_info: Dict[str, Any]):
        """
        Register an incoming shipment.

        Args:
            shipment_info: Dictionary containing shipment information
        """
        shipment_data = PersistentMapping(shipment_info)
        shipment_data["registered_at"] = self.modified_at
        self.incoming_shipments.append(shipment_data)
        self.update_modified_time()

    def add_outgoing_shipment(self, shipment_info: Dict[str, Any]):
        """
        Register an outgoing shipment.

        Args:
            shipment_info: Dictionary containing shipment information
        """
        shipment_data = PersistentMapping(shipment_info)
        shipment_data["registered_at"] = self.modified_at
        self.outgoing_shipments.append(shipment_data)
        self.update_modified_time()

    def get_capacity_utilization(self) -> Dict[str, float]:
        """
        Get capacity utilization statistics.

        Returns:
            Dictionary with utilization information
        """
        current_total = sum(self.current_inventory.values())

        utilization = {
            "total_capacity": self.max_capacity,
            "current_usage": current_total,
            "utilization_percent": (
                (current_total / self.max_capacity * 100)
                if self.max_capacity > 0
                else 0
            ),
            "remaining_capacity": max(0, self.max_capacity - current_total),
        }

        # Item-specific utilization
        for item_name, capacity in self.capacity_by_type.items():
            current_item = sum(
                v
                for k, v in self.current_inventory.items()
                if k.startswith(f"{item_name}:")
            )
            utilization[f"{item_name}_utilization"] = (
                (current_item / capacity * 100) if capacity > 0 else 0
            )

        return utilization

    def set_priority_weight(self, weight: float):
        """
        Set the priority weight for logistics routing.

        Args:
            weight: Priority weight (higher = higher priority)
        """
        self.priority_weight = weight
        self.update_modified_time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        base_dict = super().to_dict()

        inventory_dict = {
            "location": self.location,
            "facility_type": self.facility_type,
            "region": self.region,
            "coordinates": dict(self.coordinates),
            "current_inventory": dict(self.current_inventory),
            "reserved_inventory": {
                k: dict(v) for k, v in self.reserved_inventory.items()
            },
            "max_capacity": self.max_capacity,
            "capacity_by_type": dict(self.capacity_by_type),
            "priority_weight": self.priority_weight,
            "supply_priority": self.supply_priority,
            "logistics_role": self.logistics_role,
            "access_level": self.access_level,
            "authorized_users": list(self.authorized_users),
            "faction": self.faction,
            "is_operational": self.is_operational,
            "incoming_shipments_count": len(self.incoming_shipments),
            "outgoing_shipments_count": len(self.outgoing_shipments),
            "capacity_utilization": self.get_capacity_utilization(),
        }

        base_dict.update(inventory_dict)
        return base_dict
