from typing import List, Dict, Any, Optional
from services.inventory.production_nodes import ProductionNode
from services.FoxholeDataObjects.recipe import OutputType, TechnologyLevel
import time
from enum import Enum

class FacilityTrackingMode(Enum):
    """Defines the level of tracking for a facility node."""
    UNTRACKED = "untracked"  # Only track requested outputs from other nodes
    OUTPUTS_ONLY = "outputs_only"  # Track outputs for pickup task generation
    INPUTS_AND_OUTPUTS = "inputs_and_outputs"  # Track inputs and outputs, no processes

class FacilityTrackingFeatures(Enum):
    """Additional tracking features that can be enabled independently."""
    POWER = "power"  # Track power grid and generation buildings
    LIQUIDS = "liquids"  # Track pipelines and liquid connections
    MAINTENANCE_SUPPLIES = "maintenance_supplies"  # Track supply tunnel maintenance
    RESERVATIONS = "reservations"  # Track squad and facility reservations

class FacilityQueueVisibility(Enum):
    PUBLIC = "public"
    PRIVATE = "private"

class FacilityPlayerQueueStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"

class PauseReason(Enum):
    QUEUED = "queued"
    OUT_OF_MATERIALS = "out_of_materials"
    OTHER = "other"

class OperationalStatus(Enum):
    PLANNED = "planned"
    OFFLINE = "offline"
    ONLINE = "online"
    IN_PRODUCTION = "in-production"

class FacilityTrackingConfig:
    def __init__(self, mode: FacilityTrackingMode = FacilityTrackingMode.UNTRACKED, enabled_features: Optional[List[FacilityTrackingFeatures]] = None):
        self.mode = mode
        self.enabled_features = enabled_features or []
    def is_feature_enabled(self, feature: FacilityTrackingFeatures) -> bool:
        """Check if a specific tracking feature is enabled."""
        return feature in self.enabled_features
    def enable_feature(self, feature: FacilityTrackingFeatures):
        if feature not in self.enabled_features:
            self.enabled_features.append(feature)
    def disable_feature(self, feature: FacilityTrackingFeatures):
        if feature in self.enabled_features:
            self.enabled_features.remove(feature)
    def should_track_inputs(self) -> bool:
        return self.mode == FacilityTrackingMode.INPUTS_AND_OUTPUTS
    def should_track_outputs(self) -> bool:
        return self.mode in [FacilityTrackingMode.OUTPUTS_ONLY, FacilityTrackingMode.INPUTS_AND_OUTPUTS]
    def should_track_requests_only(self) -> bool:
        return self.mode == FacilityTrackingMode.UNTRACKED

class FacilityPlayerQueue:
    def __init__(self, player_id: str, visibility: FacilityQueueVisibility = FacilityQueueVisibility.PUBLIC,
                 status: FacilityPlayerQueueStatus = FacilityPlayerQueueStatus.ACTIVE,
                 pause_reason: Optional[PauseReason] = None):
        self.player_id = player_id
        self.visibility = visibility
        self.orders: List[Dict[str, Any]] = []
        self.last_interaction: float = time.time()
        self.set_status(status, pause_reason)
    def add_order(self, order: Dict[str, Any]):
        self.orders.append(order)
        self.last_interaction = time.time()
    def is_expired(self, expiry_hours: int = 24) -> bool:
        return (time.time() - self.last_interaction) > (expiry_hours * 3600)
    def set_status(self, status: FacilityPlayerQueueStatus, pause_reason: Optional[PauseReason] = None):
        self.status = status
        if status == FacilityPlayerQueueStatus.PAUSED:
            self.pause_reason = pause_reason
        else:
            self.pause_reason = None
    def get_status(self) -> FacilityPlayerQueueStatus:
        return self.status
    def get_pause_reason(self) -> Optional[PauseReason]:
        return self.pause_reason

class SquadReservation:
    # 52 hours in seconds
    EXPIRATION_SECONDS = 187200
    def __init__(self, squad_reservation: Optional[str] = None, squad_reservation_expiration: Optional[float] = None):
        self.squad_reservation: Optional[str] = squad_reservation
        self.squad_reservation_expiration: Optional[float] = squad_reservation_expiration
    def refresh_expiration(self):
        self.squad_reservation_expiration = time.time() + self.EXPIRATION_SECONDS
    def set_expiration(self, expiration_timestamp: float):
        if not isinstance(expiration_timestamp, (float, int)):
            raise ValueError("Expiration timestamp must be a float or int (unix timestamp)")
        self.squad_reservation_expiration = float(expiration_timestamp)

class PowerSwitch(SquadReservation):
    def __init__(self, squad_reservation: Optional[str] = None, squad_reservation_expiration: Optional[float] = None, state: str = "off"):
        super().__init__(squad_reservation, squad_reservation_expiration)
        self.set_state(state if state in ("on", "off") else "off")
    def set_state(self, state: str):
        if state in ("on", "off"):
            self.state = state
    def get_state(self) -> str:
        return self.state

class PowerGrid(SquadReservation):
    def __init__(self, squad_reservation: Optional[str] = None, squad_reservation_expiration: Optional[float] = None):
        super().__init__(squad_reservation, squad_reservation_expiration)
        self.producers: List['FacilityBuilding'] = []
        self.consumers: List['FacilityBuilding'] = []
        self.power_switches: List[PowerSwitch] = []
    def add_producer(self, building: 'FacilityBuilding') -> bool:
        if building not in self.producers:
            self.producers.append(building)
            return True
        return False
    def remove_producer(self, building: 'FacilityBuilding') -> bool:
        if building in self.producers:
            self.producers.remove(building)
            return True
        return False
    def get_producers(self) -> List['FacilityBuilding']:
        return self.producers
    def clear_producers(self):
        self.producers.clear()
    def add_consumer(self, building: 'FacilityBuilding') -> bool:
        if building not in self.consumers:
            self.consumers.append(building)
            return True
        return False
    def remove_consumer(self, building: 'FacilityBuilding') -> bool:
        if building in self.consumers:
            self.consumers.remove(building)
            return True
        return False
    def get_consumers(self) -> List['FacilityBuilding']:
        return self.consumers
    def clear_consumers(self):
        self.consumers.clear()
    def add_power_switch(self, switch: PowerSwitch) -> bool:
        if switch not in self.power_switches:
            self.power_switches.append(switch)
            return True
        return False
    def remove_power_switch(self, switch: PowerSwitch) -> bool:
        if switch in self.power_switches:
            self.power_switches.remove(switch)
            return True
        return False
    def get_power_switches(self) -> List[PowerSwitch]:
        return self.power_switches
    def clear_power_switches(self):
        self.power_switches.clear()
    def get_squad_reservation(self) -> Optional[str]:
        return self.squad_reservation
    def update_power_network(self):
        """Aggregate supply/demand, enforce 30 MW cap, distribute power."""
        total_supply = sum(b.power_supply for b in self.producers)
        total_demand = sum(b.power_demand for b in self.consumers)
        # Cap supply at 30 MW
        if total_supply > 30.0:
            total_supply = 30.0
        # Distribute supply to consumers proportionally
        for consumer in self.consumers:
            if total_demand > 0:
                consumer.power_supply = total_supply * (consumer.power_demand / total_demand)
            else:
                consumer.power_supply = 0.0
            consumer.update_power_state()
        # Update generators' resource consumption
        for producer in self.producers:
            # If demand is 0, stop consumption
            if total_demand == 0:
                producer.resource_consumption_multiplier = 0.0
            else:
                # If supply > demand, consume less
                producer.resource_consumption_multiplier = min(1.0, total_demand / total_supply) if total_supply > 0 else 0.0

class FacilityBuilding(ProductionNode):
    DEFAULT_STOCKPILE_LIMIT = 32000
    DEFAULT_INVENTORY_SLOTS = 15
    MAX_ACTIVE_QUEUES = 5
    QUEUE_EXPIRY_HOURS = 28
    def __init__(self, building_id: str, name: str, building_type: str, output_type: OutputType = OutputType.CRATES
                 , technology_level: TechnologyLevel = TechnologyLevel.NONE, stockpile_limit: int = None
                 , upgrade_type: Optional[str] = None, operational_status: OperationalStatus = OperationalStatus.PLANNED
                 , tracking_config: Optional[FacilityTrackingConfig] = None, disruptive_flag_required: int = 5
                 , power_demand: float = 0.0, power_supply: float = 0.0, max_building_stockpile: Optional[int] = None
                 , *args, **kwargs):
        super().__init__(building_id, name, *args, **kwargs)
        self.building_type = building_type
        self.output_type = output_type
        self.technology_level = technology_level
        self.stockpile_limit = stockpile_limit or self.DEFAULT_STOCKPILE_LIMIT
        self.subtype = upgrade_type
        self.construction_status = operational_status
        self.facility_stockpile: Dict[str, int] = {}
        self.facility_inventory: Dict[str, int] = {}
        self.player_queues: Dict[str, FacilityPlayerQueue] = {}
        self.active_queues: List[str, FacilityPlayerQueue] = []
        self.base_recipes: List[str] = []
        self.additional_recipes: List[str] = []
        self.disruptive_placement = DisruptivePlacementStatus(disruptive_flag_required)
        self.max_building_stockpile: Optional[int] = max_building_stockpile
        self.is_upgraded: bool = False
        self.upgrade_options: List[str] = []
        self.production_rates: Dict[str, float] = {}
        self.tracking_config: FacilityTrackingConfig = tracking_config or FacilityTrackingConfig()
        self.max_building_stockpile: Optional[int] = max_building_stockpile
        self.power_demand: float = power_demand
        self.power_supply: float = power_supply
        self.power_status: str = "normal"  # "normal", "slow", "shutdown"
        self.is_powered: bool = True

    def upgrade_to(self, building_type: str) -> bool:
        if not self.can_be_upgraded:
            return False
        if self.is_upgraded:
            return False
        if building_type not in self.upgrade_options:
            return False
        self.is_upgraded = True
        additional_recipes = self.fetch_recipes_for_upgrade(building_type)
        self.additional_recipes.extend(additional_recipes)
        return True

    def fetch_recipes_for_upgrade(self, building_type: str) -> List[str]:
        return [f"Recipe for {building_type}"]
    def get_all_recipes(self) -> List[str]:
        return self.base_recipes + self.additional_recipes

    def add_player_queue(self, player_id: str, visibility: FacilityQueueVisibility = FacilityQueueVisibility.PRIVATE) -> bool:
        if player_id in self.player_queues:
            return False
        self.player_queues[player_id] = FacilityPlayerQueue(player_id, visibility)
        return True
    def activate_queue(self, player_id: str) -> bool:
        if player_id not in self.player_queues:
            return False
        if len(self.active_queues) >= self.MAX_ACTIVE_QUEUES:
            return False
        if player_id in self.active_queues:
            return False
        self.active_queues.append(player_id)
        self.player_queues[player_id].set_status(FacilityPlayerQueueStatus.ACTIVE)
        return True
    def deactivate_queue(self, player_id: str) -> bool:
        if player_id in self.active_queues:
            self.active_queues.remove(player_id)
            if player_id in self.player_queues:
                self.player_queues[player_id].set_status(FacilityPlayerQueueStatus.STOPPED)
            return True
        return False

    def expire_inactive_queues(self) -> List[str]:
        expired_players = []
        for player_id, queue in list(self.player_queues.items()):
            if not queue.get_status() == FacilityPlayerQueueStatus.ACTIVE and queue.is_expired(self.QUEUE_EXPIRY_HOURS):
                self._move_queue_to_stockpile(queue)
                expired_players.append(player_id)
                del self.player_queues[player_id]
        return expired_players

    def _move_queue_to_stockpile(self, queue: FacilityPlayerQueue):
        for order in queue.orders:
            pass

    def get_total_storage_capacity(self) -> Dict[str, int]:
        base_capacity = self.stockpile_limit
        player_queue_capacity = len(self.player_queues) * self.stockpile_limit
        return {
            "facility_stockpile": base_capacity,
            "player_queues_total": player_queue_capacity,
            "facility_inventory_slots": self.DEFAULT_INVENTORY_SLOTS
        }
    def get_largest_power_order(self) -> Optional[float]:
        """Return the largest power usage from active orders."""
        # Assume each order has a 'power_usage' attribute
        largest = 0.0
        for queue in self.player_queues.values():
            for order in getattr(queue, 'orders', []):
                usage = getattr(order, 'power_usage', 0.0)
                if usage > largest:
                    largest = usage
        return largest if largest > 0 else None

    def update_power_demand_from_orders(self):
        """Update power demand to only use the largest order's usage."""
        largest = self.get_largest_power_order()
        self.power_demand = largest if largest else 0.0

    def enforce_power_building_order_logic(self):
        """Ensure only one active order for power buildings, unlimited queue."""
        # Only allow one active queue for power buildings
        if self.building_type == 'power':
            if len(self.active_queues) > 1:
                # Deactivate all but the first active queue
                for pid in self.active_queues[1:]:
                    self.deactivate_queue(pid)

    def update_resource_consumption(self, total_demand: float, total_supply: float):
        """Update resource consumption for power buildings."""
        if self.building_type == 'power':
            if total_demand == 0:
                self.resource_consumption_multiplier = 0.0
            elif total_supply > total_demand:
                self.resource_consumption_multiplier = total_demand / total_supply if total_supply > 0 else 0.0
            else:
                self.resource_consumption_multiplier = 1.0

    def get_status(self) -> dict:
        status = {
            "operational": self.is_powered,
            "power_status": self.power_status,
            "power_demand": self.power_demand,
            "power_supply": self.power_supply,
            "production_rate_multiplier": self.get_effective_production_rate(),
            "active_queues": self.active_queues,
            "queued_orders": {pid: getattr(self.player_queues[pid], 'orders', []) for pid in self.player_queues}
        }
        return status
    def update_power_state(self):
        """Update power status and production rate based on supply/demand."""
        if self.power_demand == 0:
            self.power_status = "normal"
            self.is_powered = True
            return
        ratio = self.power_supply / self.power_demand if self.power_demand > 0 else 1.0
        if ratio < 0.1:
            self.power_status = "shutdown"
            self.is_powered = False
        elif ratio < 1.0:
            self.power_status = "slow"
            self.is_powered = True
        else:
            self.power_status = "normal"
            self.is_powered = True
    def get_effective_production_rate(self) -> float:
        """Return production rate multiplier based on power status."""
        self.update_power_state()
        if self.power_status == "shutdown":
            return 0.0
        elif self.power_status == "slow":
            return self.power_supply / self.power_demand if self.power_demand > 0 else 1.0
        else:
            return 1.0
    def get_inventory(self) -> Dict[str, int]:
        total_inventory = self.facility_stockpile.copy()
        for item, qty in self.facility_inventory.items():
            total_inventory[item] = total_inventory.get(item, 0) + qty
        return total_inventory

class LiquidBuilding(FacilityBuilding):
    def __init__(self, building_id: str, name: str, building_type: str, output_type: OutputType = OutputType.CRATES, technology_level: TechnologyLevel = TechnologyLevel.NONE, stockpile_limit: int = None, upgrade_type: Optional[str] = None, operational_status: OperationalStatus = OperationalStatus.PLANNED, input_inlet: int = 0, output_inlet: int = 0, pipe_connections: Optional[list['LiquidBuilding']] = None, internal_liquid_storage_capacity: Optional[int] = None, needs_liquid_container: bool = False, liquid_container_refill: Optional[int] = None, tracking_config: Optional[FacilityTrackingConfig] = None, disruptive_flag_required: int = 5, power_demand: float = 0.0, power_supply: float = 0.0, *args, **kwargs):
        super().__init__(building_id, name, building_type, output_type, technology_level, stockpile_limit, upgrade_type, operational_status, tracking_config=tracking_config, disruptive_flag_required=disruptive_flag_required, power_demand=power_demand, power_supply=power_supply, *args, **kwargs)
        self.input_inlet: int = input_inlet
        self.output_inlet: int = output_inlet
        self.pipe_connections: list['LiquidBuilding'] = pipe_connections if pipe_connections is not None else []
        self.internal_liquid_storage_capacity: Optional[int] = internal_liquid_storage_capacity
        self.needs_liquid_container: bool = needs_liquid_container
        self.liquid_container_refill: Optional[int] = liquid_container_refill

    def add_pipe_connection(self, building: 'LiquidBuilding') -> bool:
        if building in self.pipe_connections:
            return False
        self.pipe_connections.append(building)
        return True

    def remove_pipe_connection(self, building: 'LiquidBuilding') -> bool:
        if building in self.pipe_connections:
            self.pipe_connections.remove(building)
            return True
        return False

    def update_pipe_connection(self, old_building: 'LiquidBuilding', new_building: 'LiquidBuilding') -> bool:
        try:
            idx = self.pipe_connections.index(old_building)
            self.pipe_connections[idx] = new_building
            return True
        except ValueError:
            return False

    def clear_pipe_connections(self) -> None:
        self.pipe_connections.clear()

    def get_pipe_connections(self) -> list:
        return self.pipe_connections

class FacilityTask:
    def __init__(self, task_id: str, description: str, interval_seconds: int):
        self.task_id = task_id
        self.description = description
        self.interval_seconds = interval_seconds
        self.last_completed: float = 0.0
        self.status: str = "pending"
    def complete_task(self, timestamp: float):
        self.last_completed = timestamp
        self.status = "completed"
    def is_due(self, current_time: float) -> bool:
        return (current_time - self.last_completed) >= self.interval_seconds

class FacilityStatusBoard:
    """Aggregates and presents status for the facility and its buildings/tasks."""
    def __init__(self, facility_node: 'FacilityNode'):
        self.facility_node = facility_node
    def get_status_summary(self) -> Dict[str, Any]:
        summary = {
            "facility_status": getattr(self.facility_node, "status", None),
            "buildings": [
                {
                    "name": getattr(b, "location_name", None),
                    "type": getattr(b, "building_type", None),
                    "status": b.get_status(),
                    "disruptive_placement": b.get_disruptive_flag_status() if hasattr(b, "get_disruptive_flag_status") else None,
                }
                for b in getattr(self.facility_node, "buildings", [])
            ],
            "tasks": [
                {"description": t.description, "status": t.status} for t in getattr(self.facility_node, "tasks", [])
            ],
        }
        return summary

class FacilityNode(ProductionNode):
    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate", base_type=None, production_type=None
                 , facility_type=None, process_type=None, process_label=None, output_type: Optional[str] = None
                 , building_id: Optional[str] = None, tracking_config: Optional[FacilityTrackingConfig] = None
                 , disassembled_crates: bool = False):
        super().__init__(node_id, location_name, unit_size, base_type, production_type, facility_type, process_type
                         , process_label)
        self.output_type = output_type
        self.building_id = building_id
        self.buildings: List[FacilityBuilding] = []
        self.tasks: List[FacilityTask] = []
        self.status_board = FacilityStatusBoard(self)
        self.tracking_config: FacilityTrackingConfig = tracking_config or FacilityTrackingConfig()
        self.disassembled_crates: bool = disassembled_crates
    def add_building(self, building: FacilityBuilding):
        if (building.tracking_config.mode == FacilityTrackingMode.UNTRACKED and
                not building.tracking_config.enabled_features):
            building.tracking_config = self.tracking_config
        self.buildings.append(building)

    def update_facility_tracking_config(self, tracking_config: FacilityTrackingConfig, apply_to_buildings: bool = True):
        self.tracking_config = tracking_config
        if apply_to_buildings:
            for building in self.buildings:
                building.tracking_config = tracking_config
    def get_tracking_summary(self) -> Dict[str, Any]:
        return {
            "facility_tracking_mode": self.tracking_config.mode.value,
            "facility_enabled_features": [f.value for f in self.tracking_config.enabled_features],
            "buildings": [
                {
                    "building_id": getattr(building, "node_id", None),
                    "building_type": building.building_type,
                    "tracking_mode": building.tracking_config.mode.value,
                    "enabled_features": [f.value for f in building.tracking_config.enabled_features],
                    "should_track_inputs": building.tracking_config.should_track_inputs(),
                    "should_track_outputs": building.tracking_config.should_track_outputs(),
                }
                for building in self.buildings
            ]
        }
    def add_task(self, task: FacilityTask):
        self.tasks.append(task)
    def aggregate_inventory(self) -> Dict[str, int]:
        total_inventory: Dict[str, int] = {}
        for building in self.buildings:
            building_inventory = building.get_inventory()
            for item, qty in building_inventory.items():
                total_inventory[item] = total_inventory.get(item, 0) + qty
        return total_inventory

    def aggregate_status(self) -> Dict[str, Any]:
        return self.status_board.get_status_summary()
    def get_graph_edges(self) -> List[Any]:
        return getattr(self, "edges", [])

    def add_cross_facility_request(self, item: str, quantity: int, requesting_facility_id: str):
        for building in self.buildings:
            if item in building.get_all_recipes():
                if hasattr(building, "add_output_request"):
                    building.add_output_request(item, quantity, requesting_facility_id)
                break

class DisruptivePlacementStatus:
    """Encapsulates disruptive placement flagging and state for a facility building."""
    def __init__(self, required_flags: int = 5):
        self.flags: list[dict] = []  # Each dict: {"player_id": str, "timestamp": float}
        self.required_flags: int = required_flags
        self.expiry: float | None = None
        self.is_destroyable: bool = False
        self.is_destroyed: bool = False

    def flag(self, player_id: str, timestamp: float) -> bool:
        # Remove expired flags
        if self.expiry and timestamp > self.expiry:
            self.reset()
        # Check if already flagged by this player
        for f in self.flags:
            if f["player_id"] == player_id:
                f["timestamp"] = timestamp
                break
        else:
            self.flags.append({"player_id": player_id, "timestamp": timestamp})
        # Set expiry to 24h from now if not set
        if not self.expiry:
            self.expiry = timestamp + 24 * 3600
        # Check if enough flags
        if len(self.flags) >= self.required_flags:
            self.is_destroyable = True
        return self.is_destroyable

    def reset(self):
        self.flags.clear()
        self.expiry = None
        self.is_destroyable = False

    def mark_destroyed(self):
        self.is_destroyed = True
        self.is_destroyable = False
        self.reset()

    def get_flag_count(self) -> int:
        return len(self.flags)

    def get_status(self) -> dict:
        return {
            "flag_count": self.get_flag_count(),
            "required": self.required_flags,
            "is_destroyable": self.is_destroyable,
            "is_destroyed": self.is_destroyed,
            "expiry": self.expiry,
            "flagged_by": [f["player_id"] for f in self.flags],
        }

class DisruptiveFlagTask(FacilityTask):
    """Task to track and report disruptive flag count for a building."""
    def __init__(self, building: FacilityBuilding, interval_seconds: int = 60):
        super().__init__(
            task_id=f"disruptive_flag_{building.node_id}",
            description=f"Disruptive flags for {building.name}",
            interval_seconds=interval_seconds
        )
        self.building = building

    def increment_flag(self, player_id: str, timestamp: float) -> bool:
        """Flag the building and update status."""
        return self.building.flag_disruptive_placement(player_id, timestamp)

    def get_flag_count(self) -> int:
        return self.building.get_disruptive_flag_count()

    def get_status_embed(self) -> Dict[str, any]:
        """Return status suitable for Discord embed."""
        status = self.building.get_disruptive_flag_status()
        return {
            "building": self.building.name,
            "flag_count": status["flag_count"],
            "required": status["required"],
            "is_destroyable": status["is_destroyable"],
            "is_destroyed": status["is_destroyed"],
            "flagged_by": status["flagged_by"],
            "expires_at": status["expiry"],
        }

class VehicleBuilding(FacilityBuilding):
    """
    FacilityBuilding for manufacturing/upgrades with pad and squad reservation logic.
    Supports: Vehicle Assembly, Dry Docks, A09-E Rocket Platforms.
    """
    MAX_ACTIVE_ORDERS = 1
    SQUAD_RESERVATION_DURATION = 1800  # 30 minutes in seconds
    LARGE_STATION_STORAGE_DURATION = 187200  # 52 hours in seconds

    def __init__(self, *args, accepted_stockpile_inputs: Optional[list[str]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pad_occupied: bool = False
        self.pad_vehicle: Optional[dict] = None  # Info about vehicle on pad
        self.squad_reservation: Optional[dict] = None  # {"squad_id": str, "expires_at": float}
        self.accepted_stockpile_inputs: list[str] = accepted_stockpile_inputs if accepted_stockpile_inputs is not None else []

    def is_pad_occupied(self) -> bool:
        return self.pad_occupied

    def occupy_pad(self, vehicle_info: dict):
        self.pad_occupied = True
        self.pad_vehicle = vehicle_info

    def vacate_pad(self):
        self.pad_occupied = False
        self.pad_vehicle = None
        self.squad_reservation = None

    def reserve_vehicle_for_squad(self, squad_id: str, current_time: float):
        self.squad_reservation = {
            "squad_id": squad_id,
            "expires_at": current_time + self.SQUAD_RESERVATION_DURATION
        }

    def accepts_stockpile_input(self, item: str) -> bool:
        """Check if the item is accepted for stockpile input."""
        return item in self.accepted_stockpile_inputs

    def add_order(self, player: str, order: dict, current_time: float) -> bool:
        if not self.can_add_order():
            return False
        # Add notification and squad reservation expiry to order
        order["notify_on_completion"] = order.get("notify_on_completion", False)
        order["squad_reservation_expiry"] = current_time + self.SQUAD_RESERVATION_DURATION
        # Store order in FacilityPlayerQueue
        if player not in self.player_queues:
            self.player_queues[player] = FacilityPlayerQueue(player)
        self.player_queues[player].add_order(order)
        self.active_queues.append(player)
        return True

    def is_squad_reservation_active(self, current_time: float) -> bool:
        if not self.squad_reservation or self.squad_reservation.get("expires_at") is None:
            return False
        return float(self.squad_reservation["expires_at"]) > current_time

    def can_add_order(self) -> bool:
        # Only allow one active order at a time
        return len(self.active_queues) < self.MAX_ACTIVE_ORDERS

    def calculate_completion_time(self, player: str, order: dict, current_time: float) -> dict:
        # Assume order has a duration property (seconds)
        completion_time = current_time + order.get("duration", 0)
        squad_expiration = completion_time + self.SQUAD_RESERVATION_DURATION
        return {
            "order_completion": completion_time,
            "squad_expiration": squad_expiration
        }

    def add_notification_for_completion(self, order: dict):
        # Stub for future notification logic
        pass
