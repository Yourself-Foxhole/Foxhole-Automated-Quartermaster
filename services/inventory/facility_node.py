from typing import List, Dict, Any, Optional, Union
from enum import Enum
from services.inventory.production_nodes import ProductionNode
import time

class OutputType(Enum):
    CRATES = "crates"
    ITEM = "item"
    RESOURCE = "resource"
    LIQUID = "liquid"

class TechnologyLevel(Enum):
    NONE = "none"
    TIER2 = "Tier2"
    TIER3 = "Tier3"

class QueueVisibility(Enum):
    PUBLIC = "public"
    PRIVATE = "private"

class PlayerQueue:
    """Represents a player's queue in a facility building."""
    def __init__(self, player_id: str, visibility: QueueVisibility = QueueVisibility.PRIVATE):
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

    def __init__(self, building_id: str, name: str, building_type: str,
                 output_type: OutputType = OutputType.CRATES,
                 technology_level: TechnologyLevel = TechnologyLevel.NONE,
                 stockpile_limit: int = None,
                 *args, **kwargs):
        super().__init__(building_id, name, *args, **kwargs)
        self.building_type = building_type
        self.output_type = output_type
        self.technology_level = technology_level
        self.stockpile_limit = stockpile_limit or self.DEFAULT_STOCKPILE_LIMIT

        # Storage locations
        self.facility_stockpile: Dict[str, int] = {}  # Main stockpile (up to stockpile_limit per item)
        self.facility_inventory: Dict[str, int] = {}  # 15-slot inventory for misc items

        # Queue management
        self.player_queues: Dict[str, PlayerQueue] = {}  # player_id -> PlayerQueue
        self.active_queues: List[str] = []  # List of active player IDs (max 5)

        # Recipe and upgrade system
        self.base_recipes: List[str] = []  # Recipes available at base level
        self.additional_recipes: List[str] = []  # Recipes added through upgrades
        self.can_be_upgraded: bool = False
        self.upgrade_options: List[str] = []  # List of possible upgrade building types
        self.is_upgraded: bool = False
        self.upgrade_type: Optional[str] = None

        # Production calculation
        self.production_rates: Dict[str, float] = {}  # recipe -> items per hour

    def get_all_recipes(self) -> List[str]:
        """Get all available recipes (base + additional from upgrades)."""
        return self.base_recipes + self.additional_recipes

    def add_player_queue(self, player_id: str, visibility: QueueVisibility = QueueVisibility.PRIVATE) -> bool:
        """Add a new player queue. Returns True if successful."""
        if player_id in self.player_queues:
            return False  # Queue already exists

        self.player_queues[player_id] = PlayerQueue(player_id, visibility)
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

    def _move_queue_to_stockpile(self, queue: PlayerQueue):
        """Move items from expired queue to facility stockpile, deleting overflow."""
        for order in queue.orders:
            # This would need to be implemented based on specific order structure
            # For now, just a placeholder
            pass

    def calculate_completion_time(self, recipe: str, quantity: int) -> float:
        """Calculate when a recipe will be completed given current production rate."""
        if recipe not in self.production_rates:
            return 0.0

        rate = self.production_rates[recipe]  # items per hour
        if rate <= 0:
            return float('inf')

        hours_needed = quantity / rate
        return time.time() + (hours_needed * 3600)

    def calculate_stockpile_at_time(self, target_time: float) -> Dict[str, int]:
        """Calculate what will be in the facility stockpile at a given future time."""
        # This would implement production simulation
        # For now, return current stockpile
        return self.facility_stockpile.copy()

    def upgrade_to(self, upgrade_type: str) -> bool:
        """Upgrade this building to a specific type."""
        if not self.can_be_upgraded:
            return False
        if self.is_upgraded:
            return False  # Already upgraded
        if upgrade_type not in self.upgrade_options:
            return False

        self.is_upgraded = True
        self.upgrade_type = upgrade_type
        # Additional recipes would be added based on upgrade type
        return True

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
        return self.status

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
                {"name": b.location_name, "type": b.building_type, "status": b.get_status()} for b in self.facility_node.buildings
            ],
            "tasks": [
                {"description": t.description, "status": t.status} for t in self.facility_node.tasks
            ]
        }
        return summary

class FacilityNode(ProductionNode):
    """Represents a player-built facility, aggregates buildings and tasks, exposes only itself to the graph."""
    def __init__(self, node_id: str, location_name: str, unit_size: str = "crate", base_type=None, production_type=None, facility_type=None, process_type=None, process_label=None):
        super().__init__(node_id, location_name, unit_size, base_type, production_type, facility_type, process_type, process_label)
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
    """Base class for power-related buildings."""
    pass

class DieselPowerPlant(PowerBuilding):
    """Diesel Power Plant."""
    pass

class PowerStationBuilding(PowerBuilding):
    """Power Station."""
    pass

class ResourceBuilding(FacilityBuilding):
    """Base class for resource extraction buildings."""
    pass

class OilWell(ResourceBuilding):
    """Oil Well."""
    pass

class WaterPump(ResourceBuilding):
    """Water Pump."""
    pass

class StationaryHarvester(ResourceBuilding):
    """Stationary Harvester."""
    pass

class FacilityRefinery(FacilityBuilding):
    """Base class for refinery buildings."""
    pass

class CoalRefinery(FacilityRefinery):
    """Coal Refinery."""
    pass

class OilRefinery(FacilityRefinery):
    """Oil Refinery."""
    pass

class ConcreteMixer(FacilityRefinery):
    """Concrete Mixer."""
    pass

class ItemProductionBuilding(FacilityBuilding):
    """Base class for item production buildings."""
    pass

class AmmoFactory(ItemProductionBuilding):
    """Ammo Factory with upgrade system."""

    def __init__(self, building_id: str, name: str, *args, **kwargs):
        super().__init__(building_id, name, "AmmoFactory",
                        output_type=OutputType.CRATES,
                        technology_level=TechnologyLevel.NONE,
                        *args, **kwargs)

        # Base ammo factory recipes (these would come from static data)
        self.base_recipes = [
            # Add more base recipes as needed
        ]

        # Upgrade system
        self.can_be_upgraded = True
        self.upgrade_options = [
            "RocketBatteryWorkshop",
            "LargeShellFactory",
            "TripodFactory"
        ]

    def upgrade_to_rocket_battery_workshop(self) -> bool:
        """Upgrade to Rocket Battery Workshop."""
        if self.upgrade_to("RocketBatteryWorkshop"):
            self.additional_recipes.extend([
                # Add rocket-specific recipes
            ])
            return True
        return False

    def upgrade_to_large_shell_factory(self) -> bool:
        """Upgrade to Large Shell Factory."""
        if self.upgrade_to("LargeShellFactory"):
            self.additional_recipes.extend([
                "120mm",
                "150mm",
                "300mm",
                # Add large shell recipes
            ])
            return True
        return False

    def upgrade_to_tripod_factory(self) -> bool:
        """Upgrade to Tripod Factory."""
        if self.upgrade_to("TripodFactory"):
            self.additional_recipes.extend([
                "Tripod",
                "Tripod Weapon Systems",
                # Add tripod recipes
            ])
            return True
        return False

class RocketBatteryWorkshop(AmmoFactory):
    """Rocket Battery Workshop - upgraded Ammo Factory."""

    def __init__(self, building_id: str, name: str, *args, **kwargs):
        super().__init__(building_id, name, *args, **kwargs)
        self.building_type = "RocketBatteryWorkshop"
        self.is_upgraded = True
        self.upgrade_type = "RocketBatteryWorkshop"

        # Add rocket-specific recipes
        self.additional_recipes = [
            "RPG Shell",
            "Rocket",
            # Add more rocket recipes
        ]

class LargeShellFactory(AmmoFactory):
    """Large Shell Factory - upgraded Ammo Factory."""

    def __init__(self, building_id: str, name: str, *args, **kwargs):
        super().__init__(building_id, name, *args, **kwargs)
        self.building_type = "LargeShellFactory"
        self.is_upgraded = True
        self.upgrade_type = "LargeShellFactory"

        # Add large shell recipes
        self.additional_recipes = [
            "120mm",
            "150mm",
            "300mm",
            # Add more large shell recipes
        ]


class TripodFactory(AmmoFactory):
    """Tripod Factory - upgraded Ammo Factory."""

    def __init__(self, building_id: str, name: str, *args, **kwargs):
        super().__init__(building_id, name, *args, **kwargs)
        self.building_type = "TripodFactory"
        self.is_upgraded = True
        self.upgrade_type = "TripodFactory"

        # Add tripod recipes
        self.additional_recipes = [
            "Tripod",
            "Tripod Weapon Systems",
            # Add more tripod recipes
        ]

class InfantryKitFactory(ItemProductionBuilding):
    """Infantry Kit Factory."""
    pass

class SpecialIssueFirearmsAssembly(InfantryKitFactory):
    """Special Issue Firearms Assembly."""
    pass

class SmallArmsWorkshop(InfantryKitFactory):
    """Small Arms Workshop."""
    pass

class HeavyMunitionsFoundry(InfantryKitFactory):
    """Heavy Munitions Foundry."""
    pass

class MaterialsFactory(ItemProductionBuilding):
    """Materials Factory."""
    pass

class AssemblyBay(MaterialsFactory):
    """Assembly Bay."""
    pass

class Forge(MaterialsFactory):
    """Forge."""
    pass

class MetalPress(MaterialsFactory):
    """Metal Press."""
    pass

class Smelter(MaterialsFactory):
    """Smelter."""
    pass

class MetalworksFactory(ItemProductionBuilding):
    """Metalworks Factory."""
    pass

class Recycler(MetalworksFactory):
    """Recycler."""
    pass

class BlastFurnace(MetalworksFactory):
    """Blast Furnace."""
    pass

class EngineeringStation(MetalworksFactory):
    """Engineering Station."""
    pass

class FacilityStorage(FacilityBuilding):
    """Base class for facility storage buildings."""
    pass

class ResourceTransferStation(FacilityStorage):
    """Resource Transfer Station."""
    pass

class LiquidTransferStation(FacilityStorage):
    """Liquid Transfer Station."""
    pass

class MaterialTransferStation(FacilityStorage):
    """Material Transfer Station."""
    pass

class CrateTransferStation(FacilityStorage):
    """Crate Transfer Station."""
    pass

class FacilityVehicleBuilding(FacilityBuilding):
    """Base class for vehicle-related buildings."""
    pass

class SmallAssemblyStation(FacilityVehicleBuilding):
    """Small Assembly Station."""
    pass

class LargeAssemblyStation(FacilityVehicleBuilding):
    """Large Assembly Station."""
    pass

class DryDock(FacilityVehicleBuilding):
    """Dry Dock."""
    pass

class FieldModificationCenter(FacilityVehicleBuilding):
    """Field Modification Center."""
    pass

class A0E9RocketPlatform(FacilityVehicleBuilding):
    """A0E-9 Rocket Platform."""
    pass

class FacilityUtility(FacilityBuilding):
    """Base class for utility/maintenance buildings."""
    pass

class MaintenanceTunnel(FacilityUtility):
    """Maintenance Tunnel."""
    pass

class PowerSwitch(FacilityUtility):
    """Power Switch."""
    pass

class SmallGaugeTrain(FacilityUtility):
    """Small Gauge Train."""
    pass

class LargeGaugeTrain(FacilityUtility):
    """Large Gauge Train."""
    pass

class CraneStorage(FacilityUtility):
    """Crane Storage."""
    pass

class SiteInspection(FacilityUtility):
    """Site Inspection."""
    pass
