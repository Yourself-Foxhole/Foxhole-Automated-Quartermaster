from typing import Dict, List, Optional, Any, Protocol
from services.FoxholeDataObjects.processes import ProductionType, FacilityType, ProcessType, PRODUCTION_PROCESS_MAP
from enum import Enum
from services.inventory.inventory_graph import InventoryNode, InventoryEdge

class BaseType(Enum):
    RESOURCE = "Resource"
    REFINERY = "CrudeOil"
    PRODUCTION = "Production"
    CRATE_NODE = "CrateNode"
    ITEM_NODE = "ItemNode"
    FACILITY = "Facility"

class BaseNode:
    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate"
                 , base_type: BaseType = BaseType.ITEM_NODE):
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

    def add_edge(self, edge: 'InventoryEdge'):
        self.edges.append(edge)

    def compute_delta_from_orders(self):
        """
        Compute delta based on orders from downstream nodes.
        Aggregates orders from all connected edges.
        """
        total_orders: Dict[str, int] = {}
        for edge in self.edges:
            if hasattr(edge, 'get_orders'):
                for order in edge.get_orders():
                    item = order.item
                    quantity = order.quantity
                    total_orders[item] = total_orders.get(item, 0) + quantity
        self.delta = total_orders

class ProductionProcessSupport(Protocol):
    def get_production_processes(self) -> List[str]:
        ...
    def supports_production_process(self, process_label: str) -> bool:
        ...

class ProductionNode(BaseNode, ProductionProcessSupport):
    SUPPORTED_PROCESSES: list[str] = []

    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate", base_type: BaseType = BaseType.PRODUCTION,
                 production_type: ProductionType | None = None, facility_type: FacilityType | None = None,
                 process_type: ProcessType | None = None, process_label: str | None = None):
        super().__init__(node_id, location_name, unit_size, base_type)
        self.production_type = production_type
        self.facility_type = facility_type
        self.process_type = process_type
        self.process_label = process_label
        self.in_production: dict[str, dict[str, Any]] = {}  # item -> status/quantity
        self.set_production_processes()

    def set_production_processes(self, processes: list[str] | None = None):
        """
        Sets the production processes for this node. Can be overloaded in subclasses.
        Call super().set_production_processes() to extend logic.
        """
        self.processes = processes or []

    def get_production_processes(self) -> list[str]:
        # Only return processes if set by concrete class
        return getattr(self, "processes", [])

    def supports_production_process(self, process_label: str) -> bool:
        return process_label in self.get_production_processes()

class QueueableProductionNode(ProductionNode):
    QUEUE_EXPIRY_WARNING_SECONDS = 15 * 60  # 15 minutes before expiration

    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate", base_type: BaseType = BaseType.PRODUCTION,
                 production_type: ProductionType | None = None, facility_type: FacilityType | None = None,
                 process_type: ProcessType | None = None, process_label: str | None = None):
        super().__init__(node_id, location_name, unit_size, base_type, production_type, facility_type, process_type, process_label)
        self.queue_expiration: dict[str, float] = {}  # player -> expiration timestamp
        self.production_queue: dict[str, list[dict[str, Any]]] = {}  # player -> queue of items

    def add_to_queue(self, player: str, order: Dict[str, Any]):
        if player not in self.production_queue:
            self.production_queue[player] = []
        self.production_queue[player].append(order)

    def set_queue_expiration(self, player: str, expiration: float):
        self.queue_expiration[player] = expiration

    def get_player_queue(self, player: str) -> List[Dict[str, Any]]:
        return self.production_queue.get(player, [])

    def check_queue_expiry_warnings(self):
        import time
        now = time.time()
        for player, expiration in self.queue_expiration.items():
            time_left = expiration - now
            if 0 < time_left < self.QUEUE_EXPIRY_WARNING_SECONDS:
                self.notify_queue_expiry_warning(player, time_left)

    def notify_queue_expiry_warning(self, player: str, time_left: float):
        # Placeholder for notification logic to be implemented in presentation layer
        # For now, just print (replace with event dispatch in future)
        print(f"[Queue Expiry Warning] Player '{player}' queue will expire in {int(time_left // 60)} minutes.")

    def add_production_order(self, item: str, quantity: int, target_node: 'InventoryNode', required_resources: Optional[Dict[str, int]] = None):
        """
        Create a production order and attach to the appropriate edge.
        If resources are missing, mark as blocked and list missing resources.
        """
        from services.inventory.order import Order
        missing_resources = []
        if required_resources:
            for res, amt in required_resources.items():
                if self.inventory.get(res, 0) < amt:
                    missing_resources.append(res)
        status = "blocked" if missing_resources else "queued"
        order = Order(item, quantity, self, target_node, status=status, order_type="production", blocking_resources=missing_resources)
        # Attach order to edge
        for edge in self.edges:
            if edge.target == target_node:
                edge.add_order(order)
                break

class RefineryNode(QueueableProductionNode):
    pass

class FactoryNode(QueueableProductionNode):
    SUPPORTED_PROCESSES = [
        "Uniform::Factory",
        "SmallArms::Factory",
        "HeavyArms::Factory",
        "HeavyAmmo::Factory",
        "Utility::Factory",
        "Medical::Factory",
        "MaintenanceSupplies::Factory"
    ]
    MAX_CRATES_PER_ORDER = 4
    MAX_ACTIVE_PLAYERS = 6
    ORDER_EXPIRATION_SECONDS = 60 * 60  # 60 minutes

    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate", base_type: BaseType = BaseType.PRODUCTION,
                 production_type: ProductionType | None = None, facility_type: FacilityType | None = None,
                 process_type: ProcessType | None = None, process_label: str | None = None):
        super().__init__(node_id, location_name, unit_size, base_type, production_type, facility_type, process_type, process_label)
        self.set_production_processes(self.SUPPORTED_PROCESSES)

    def add_production_order(self, item: str, quantity: int, target_node: InventoryNode, required_resources: Optional[Dict[str, int]] = None):
        process_label = required_resources.get("process_label") if required_resources else None
        if process_label and process_label not in self.SUPPORTED_PROCESSES:
            raise ValueError(f"Process '{process_label}' not supported by FactoryNode.")
        num_crates = required_resources.get("num_crates", 1) if required_resources else 1
        if num_crates > self.MAX_CRATES_PER_ORDER:
            raise ValueError(f"Cannot produce more than {self.MAX_CRATES_PER_ORDER} crates per order.")
        # Add order and set expiration
        super().add_production_order(item, quantity, target_node, required_resources)

    def expire_orders(self):
        # Edge-based: expire orders by status/timestamp if needed
        import time
        now = time.time()
        expired_orders = []
        for edge in self.edges:
            for order in edge.get_orders():
                if hasattr(order, 'created_at') and order.status == "queued":
                    if order.created_at and now - order.created_at > self.ORDER_EXPIRATION_SECONDS:
                        order.update_status("expired", now)
                        expired_orders.append(order)
        return expired_orders

    def get_active_players(self) -> List[str]:
        # Edge-based: return unique sources of active orders
        active_players = set()
        for edge in self.edges:
            for order in edge.get_orders():
                if order.status in ["queued", "blocked"]:
                    active_players.add(order.source.node_id)
        return list(active_players)

class MassProductionFactoryNode(QueueableProductionNode):
    SUPPORTED_PROCESSES = [
        "SmallArms::MPF",
        "HeavyArms::MPF",
        "HeavyAmmo::MPF",
        "MaintenanceSupplies::MPF",
        "Uniform::MPF",
        "Vehicle::MPF",
        "Ship::MPF",
        "Shippable::MPF"
    ]
    MPF_CRATE_DISCOUNTS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.333333, 0.357143, 0.375, 0.388889]

    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate", base_type: BaseType = BaseType.PRODUCTION,
                 production_type: ProductionType | None = None, facility_type: FacilityType | None = None,
                 process_type: ProcessType | None = None, process_label: str | None = None):
        super().__init__(node_id, location_name, unit_size, base_type, production_type, facility_type, process_type, process_label)
        self.set_production_processes(self.SUPPORTED_PROCESSES)

    def add_production_order(self, item: str, quantity: int, target_node: InventoryNode, required_resources: Optional[Dict[str, int]] = None):
        process_label = required_resources.get("process_label") if required_resources else None
        if process_label not in self.SUPPORTED_PROCESSES:
            raise ValueError(f"Process '{process_label}' not supported by MassProductionFactoryNode.")
        # Shared queue for Vehicle::MPF and Ship::MPF is now edge-based
        super().add_production_order(item, quantity, target_node, required_resources)

    @staticmethod
    def get_crate_discount_percentage(self, num_crates: int) -> float:
        """
        Returns the cached discount percentage for the given number of crates (1-9).
        If num_crates is out of range, returns the closest available value.
        """
        idx = max(0, min(num_crates - 1, len(self.MPF_CRATE_DISCOUNTS) - 1))
        return self.MPF_CRATE_DISCOUNTS[idx]

    @staticmethod
    def calculate_crate_cost(self, num_crates: int, base_resource_amount: float) -> float:
        """
        Returns the total cost using the cached discount percentage for the given number of crates.
        Multiplies the base resource amount by (1 - discount).

        This uses a lookup table with the discounts prepopulated.
        """
        discount = self.get_crate_discount_percentage(num_crates)
        return base_resource_amount * (1 - discount)

    @staticmethod
    def calculate_crate_cost_slow(num_crates: int, base_cost: float, item_type: str) -> float:
        """
        Returns the total cost after MPF discount for the given number of crates.
        Vehicles and shippables: max 5 crates (max 50% discount, average 30% across whole queue).
        All other categories: max 9 crates (max 50% discount, average 38.8889% across whole queue).
        """
        if item_type in ["vehicle", "shippable"]:
            max_crates = 5
        else:
            max_crates = 9
        discount_crates = min(num_crates, max_crates)
        discount = 0.1 * discount_crates  # 10% per crate up to max
        effective_cost = base_cost * (1 - discount)
        return effective_cost

    @staticmethod
    def calculate_production_time(self, num_orders: int, item_type: str) -> float:
        """
        Returns the effective production time per order based on queue size and item type.
        For item crates: max speedup is 15x
        For vehicle/shippable crates: max speedup is 12x
        Uses straight-line slopes to calculate time based on number of orders.
        """
        if not 1 <= num_orders <= 25:
            raise ValueError(f"Input value {num_orders} is not within the 1-25 range for the MPF.")

        if item_type in ["vehicle", "shippable"]:
            return 0.4791666667 * num_orders + 0.5208333333
        else:
            return 0.5833333333 * num_orders + 0.4166666667


    def get_density_info(self, item_type: str) -> dict:
        """
        Returns density info for the item type.
        For vehicles/shippables, output is a ShippableCrate with 3 items, only unpackable at LogiStorage.
        For item crates, standard crate size applies.
        """
        if item_type in ["vehicle", "structure", "shippable"]:
            return {
                "crate_type": "ShippableCrate",
                "items_per_crate": 3,
                "unpack_location": "LogiStorage"
            }
        else:
            return {
                "crate_type": "StandardCrate",
                "items_per_crate": 1,
                "unpack_location": "Any"
            }


class CharacterProductionNode(ProductionNode):
    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate", base_type: BaseType = BaseType.PRODUCTION,
                 production_type: ProductionType | None = None, facility_type: FacilityType | None = None,
                 process_type: ProcessType | None = None, process_label: str | None = None,
                 supported_processes: list[str] | None = None):
        super().__init__(node_id, location_name, unit_size, base_type, production_type, facility_type, process_type, process_label)
        self.instant_build: bool = True  # disables queue logic
        if supported_processes:
            self.set_production_processes(supported_processes)

    def build_item(self, item: str, quantity: int):
        # Simulate instant build
        self.inventory[item] = self.inventory.get(item, 0) + quantity
