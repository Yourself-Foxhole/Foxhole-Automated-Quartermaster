from typing import List, Dict, Any, Optional
from services.inventory.production_nodes import ProductionNode
from services.FoxholeDataObjects.recipe import OutputType, TechnologyLevel
import time
from enum import Enum
from services.FoxholeDataObjects.production_time import calculate_completion_time, calculate_output_at_time

class FacilityQueueVisibility(Enum):
    PUBLIC = "public"
    PRIVATE = "private"

class FacilityPlayerQueue:
    """Represents a player's queue in a facility building."""
    def __init__(self, player_id: str, visibility: FacilityQueueVisibility = FacilityQueueVisibility.PUBLIC):
        self.player_id = player_id
        self.visibility = visibility
        self.orders: List[Dict[str, Any]] = []
        self.last_interaction: float = time.time()
        self.is_active: bool = False

    def add_order(self, order: Dict[str, Any]):
        """Add an order to this player's queue."""
        self.orders.append(order)
        self.last_interaction = time.time()

    def is_expired(self, expiry_hours: int = 24) -> bool:
        """Check if this queue has expired (default 24 hours)."""
        return (time.time() - self.last_interaction) > (expiry_hours * 3600)

class FacilityBuilding(ProductionNode):
    """Represents a single building within a facility (e.g., Factory, Power Station)."""

    # Default stockpile limits - can be overridden in subclasses
    DEFAULT_STOCKPILE_LIMIT = 32000
    DEFAULT_INVENTORY_SLOTS = 15
    MAX_ACTIVE_QUEUES = 5
    QUEUE_EXPIRY_HOURS = 24

    def __init__(
        self,
        building_id: str,
        name: str,
        building_type: str,
        output_type: OutputType = OutputType.CRATES,
        technology_level: TechnologyLevel = TechnologyLevel.NONE,
        stockpile_limit: int = None,
        *args,
        **kwargs,
    ):
        super().__init__(building_id, name, *args, **kwargs)
        self.building_type = building_type
        self.output_type = output_type
        self.technology_level = technology_level
        self.stockpile_limit = stockpile_limit or self.DEFAULT_STOCKPILE_LIMIT

        # Storage locations
        self.facility_stockpile: Dict[str, int] = {}  # Main stockpile (up to stockpile_limit per item)
        self.facility_inventory: Dict[str, int] = {}  # 15-slot inventory for misc items

        # Queue management
        self.player_queues: Dict[str, FacilityPlayerQueue] = {}  # player_id -> PlayerQueue
        self.active_queues: List[str] = []  # List of active player IDs (max 5)

        # Upgrade and recipe management
        self.base_recipes: List[str] = []
        self.additional_recipes: List[str] = []
        self.can_be_upgraded: bool = False
        self.is_upgraded: bool = False
        self.upgrade_options: List[str] = []

        # Production rates
        self.production_rates: Dict[str, float] = {}  # recipe -> items per hour

    def upgrade_to(self, building_type: str) -> bool:
        """Upgrade the facility building to a specific type."""
        if not self.can_be_upgraded:
            return False
        if self.is_upgraded:
            return False  # Already upgraded
        if building_type not in self.upgrade_options:
            return False

        self.is_upgraded = True
        # Simulate fetching additional recipes from a database
        additional_recipes = self.fetch_recipes_for_upgrade(building_type)
        self.additional_recipes.extend(additional_recipes)
        return True

    def fetch_recipes_for_upgrade(self, building_type: str) -> List[str]:
        """Placeholder for fetching recipes from a database."""
        # This would query the database in a real implementation
        return [f"Recipe for {building_type}"]

    def get_all_recipes(self) -> List[str]:
        """Get all available recipes (base + additional)."""
        return self.base_recipes + self.additional_recipes

    def add_player_queue(self, player_id: str, visibility: FacilityQueueVisibility = FacilityQueueVisibility.PRIVATE) -> bool:
        """Add a new player queue. Returns True if successful."""
        if player_id in self.player_queues:
            return False  # Queue already exists

        self.player_queues[player_id] = FacilityPlayerQueue(player_id, visibility)
        return True

    def activate_queue(self, player_id: str) -> bool:
        """Activate a player's queue. Returns True if successful."""
        if player_id not in self.player_queues:
            return False
        if len(self.active_queues) >= self.MAX_ACTIVE_QUEUES:
            return False
        if player_id in self.active_queues:
            return False  # Already active

        self.active_queues.append(player_id)
        self.player_queues[player_id].is_active = True
        return True

    def deactivate_queue(self, player_id: str) -> bool:
        """Deactivate a player's queue."""
        if player_id in self.active_queues:
            self.active_queues.remove(player_id)
            if player_id in self.player_queues:
                self.player_queues[player_id].is_active = False
            return True
        return False

    def expire_inactive_queues(self) -> List[str]:
        """Check for expired queues and move their contents to public stockpile. Returns list of expired players."""
        expired_players = []

        for player_id, queue in list(self.player_queues.items()):
            if not queue.is_active and queue.is_expired(self.QUEUE_EXPIRY_HOURS):
                # Move queue contents to facility stockpile (with overflow deletion)
                self._move_queue_to_stockpile(queue)
                expired_players.append(player_id)
                del self.player_queues[player_id]

        return expired_players

    def _move_queue_to_stockpile(self, queue: FacilityPlayerQueue):
        """Move items from expired queue to facility stockpile, deleting overflow."""
        for order in queue.orders:
            # This would need to be implemented based on specific order structure
            # For now, just a placeholder
            pass

    def get_total_storage_capacity(self) -> Dict[str, int]:
        """Get total storage capacity including all player queues."""
        base_capacity = self.stockpile_limit
        player_queue_capacity = len(self.player_queues) * self.stockpile_limit

        return {
            "facility_stockpile": base_capacity,
            "player_queues_total": player_queue_capacity,
            "facility_inventory_slots": self.DEFAULT_INVENTORY_SLOTS
        }

    def get_status(self) -> str:
        """Placeholder for building status."""
        return "operational"

    def get_inventory(self) -> Dict[str, int]:
        """Return aggregated inventory from all storage locations."""
        total_inventory = self.facility_stockpile.copy()

        # Add facility inventory
        for item, qty in self.facility_inventory.items():
            total_inventory[item] = total_inventory.get(item, 0) + qty

        # Add player queue contents (this would need specific implementation)
        # For now, just return facility stockpile + inventory
        return total_inventory

class FacilityTask:
    """Represents a recurring or scheduled task for the facility."""
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
            "facility_status": self.facility_node.status,
            "buildings": [
                {
                    "name": b.location_name,
                    "type": b.building_type,
                    "status": b.get_status(),
                }
                for b in self.facility_node.buildings
            ],
            "tasks": [
                {"description": t.description, "status": t.status} for t in self.facility_node.tasks
            ],
        }
        return summary

class FacilityNode(ProductionNode):
    """Represents a player-built facility, aggregates buildings and tasks, exposes only itself to the graph."""
    def __init__(
        self,
        node_id: str,
        location_name: str,
        unit_size: str = "crate",
        base_type=None,
        production_type=None,
        facility_type=None,
        process_type=None,
        process_label=None,
        output_type: Optional[str] = None,
        building_id: Optional[str] = None,
    ):
        super().__init__(
            node_id,
            location_name,
            unit_size,
            base_type,
            production_type,
            facility_type,
            process_type,
            process_label,
        )
        self.output_type = output_type
        self.building_id = building_id

        # Initialize attributes
        self.buildings: List[FacilityBuilding] = []
        self.tasks: List[FacilityTask] = []
        self.status_board = FacilityStatusBoard(self)

    def add_building(self, building: FacilityBuilding):
        self.buildings.append(building)

    def add_task(self, task: FacilityTask):
        self.tasks.append(task)

    def aggregate_inventory(self) -> Dict[str, int]:
        total_inventory: Dict[str, int] = {}
        for building in self.buildings:
            for item, qty in building.get_inventory().items():
                total_inventory[item] = total_inventory.get(item, 0) + qty
        return total_inventory

    def aggregate_status(self) -> Dict[str, Any]:
        return self.status_board.get_status_summary()

    def get_graph_edges(self) -> List[Any]:
        # Only expose the facility node itself, not its buildings/tasks
        return self.edges

class PowerBuilding(FacilityBuilding):
    """Represents power-related buildings."""
    pass

class LiquidBuilding(FacilityBuilding):
    """Represents buildings handling liquids (e.g., Oil Well, Water Pump)."""
    def __init__(self, *args, pipeline_input: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.pipeline_input = pipeline_input

class RawResourceBuilding(FacilityBuilding):
    """Represents raw resource extraction buildings."""
    pass

class MaterialBuilding(FacilityBuilding):
    """Represents material production buildings."""
    def __init__(
        self,
        building_id: str,
        name: str,
        building_type: str,
        output_type: OutputType = OutputType.CRATES,
        technology_level: TechnologyLevel = TechnologyLevel.NONE,
        stockpile_limit: int = None,
        *args,
        **kwargs,
    ):
        super().__init__(
            building_id,
            name,
            building_type,
            output_type,
            technology_level,
            stockpile_limit,
            *args,
            **kwargs,
        )

    def calculate_production_rate(self, recipe: str, quantity: int) -> float:
        """Calculate the production rate for a given recipe and quantity."""
        if recipe not in self.base_recipes + self.additional_recipes:
            return 0.0

        # Placeholder logic for production rate calculation
        return quantity / 10.0  # Example: 10 units per hour

    def simulate_production(self, recipe: str, hours: int) -> int:
        """Simulate production for a given recipe over a number of hours."""
        rate = self.calculate_production_rate(recipe, 1)
        return int(rate * hours)

class CrateBuilding(FacilityBuilding):
    """Represents buildings handling crates."""
    pass

class VehicleBuilding(FacilityBuilding):
    """Represents vehicle-related buildings."""
    pass

class AdvancedProductionBuilding(FacilityBuilding):
    """Represents advanced structures and buildings with unique behaviors.

    At the moment this is things like the Rocket (nuke), Dry Dock,
     and Advanced Structure Components"""
    pass

class FacilityUtility(FacilityBuilding):
    """Represents utility/maintenance buildings."""
    pass