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

class FacilityBuilding(ProductionNode):
    DEFAULT_STOCKPILE_LIMIT = 32000
    DEFAULT_INVENTORY_SLOTS = 15
    MAX_ACTIVE_QUEUES = 5
    QUEUE_EXPIRY_HOURS = 28
    def __init__(self, building_id: str, name: str, building_type: str, output_type: OutputType = OutputType.CRATES, technology_level: TechnologyLevel = TechnologyLevel.NONE, stockpile_limit: int = None, upgrade_type: Optional[str] = None, operational_status: OperationalStatus = OperationalStatus.PLANNED, has_pipe_connection: bool = False, input_inlet: int = 0, output_inlet: int = 0, pipe_connections: Optional[List['FacilityBuilding']] = None, power_grids: Optional[List[PowerGrid]] = None, has_internal_liquid_storage: bool = False, internal_liquid_storage_capacity: int = 0, needs_liquid_container: bool = False, liquid_container_refill: Optional[int] = None, tracking_config: Optional[FacilityTrackingConfig] = None, *args, **kwargs):
        super().__init__(building_id, name, *args, **kwargs)
        self.building_type = building_type
        self.output_type = output_type
        self.technology_level = technology_level
        self.stockpile_limit = stockpile_limit or self.DEFAULT_STOCKPILE_LIMIT
        self.subtype = upgrade_type
        self.construction_status = operational_status
        self.has_pipe_connection: bool = has_pipe_connection
        self.input_inlet: int = input_inlet
        self.output_inlet: int = output_inlet
        self.pipe_connections: List['FacilityBuilding'] = pipe_connections if pipe_connections is not None else []
        self.has_internal_liquid_storage: bool = has_internal_liquid_storage
        self.internal_liquid_storage_capacity: int = internal_liquid_storage_capacity
        self.needs_liquid_container: bool = needs_liquid_container
        self.liquid_container_refill: Optional[int] = liquid_container_refill
        self.facility_stockpile: Dict[str, int] = {}
        self.facility_inventory: Dict[str, int] = {}
        self.player_queues: Dict[str, FacilityPlayerQueue] = {}
        self.active_queues: List[str] = []
        self.base_recipes: List[str] = []
        self.additional_recipes: List[str] = []
        self.can_be_upgraded: bool = False
        self.is_upgraded: bool = False
        self.upgrade_options: List[str] = []
        self.production_rates: Dict[str, float] = {}
        self.power_grids: List[PowerGrid] = power_grids if power_grids is not None else []
        self.tracking_config: FacilityTrackingConfig = tracking_config or FacilityTrackingConfig()
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
    def get_status(self) -> str:
        return "operational"
    def get_inventory(self) -> Dict[str, int]:
        total_inventory = self.facility_stockpile.copy()
        for item, qty in self.facility_inventory.items():
            total_inventory[item] = total_inventory.get(item, 0) + qty
        return total_inventory
    def add_pipe_connection(self, building: 'FacilityBuilding') -> bool:
        if building in self.pipe_connections:
            return False
        self.pipe_connections.append(building)
        return True
    def remove_pipe_connection(self, building: 'FacilityBuilding') -> bool:
        if building in self.pipe_connections:
            self.pipe_connections.remove(building)
            return True
        return False
    def update_pipe_connection(self, old_building: 'FacilityBuilding', new_building: 'FacilityBuilding') -> bool:
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
                }
                for b in getattr(self.facility_node, "buildings", [])
            ],
            "tasks": [
                {"description": t.description, "status": t.status} for t in getattr(self.facility_node, "tasks", [])
            ],
        }
        return summary

class FacilityNode(ProductionNode):
    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate", base_type=None, production_type=None, facility_type=None, process_type=None, process_label=None, output_type: Optional[str] = None, building_id: Optional[str] = None, tracking_config: Optional[FacilityTrackingConfig] = None):
        super().__init__(node_id, location_name, unit_size, base_type, production_type, facility_type, process_type, process_label)
        self.output_type = output_type
        self.building_id = building_id
        self.buildings: List[FacilityBuilding] = []
        self.tasks: List[FacilityTask] = []
        self.status_board = FacilityStatusBoard(self)
        self.tracking_config: FacilityTrackingConfig = tracking_config or FacilityTrackingConfig()
    def add_building(self, building: FacilityBuilding):
        if building.tracking_config.mode == FacilityTrackingMode.UNTRACKED and not building.tracking_config.enabled_features:
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
