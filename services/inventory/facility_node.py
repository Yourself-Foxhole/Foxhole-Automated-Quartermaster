from typing import List, Dict, Any
from services.inventory.production_nodes import ProductionNode

class FacilityBuilding(ProductionNode):
    """Represents a single building within a facility (e.g., Factory, Power Station)."""
    def __init__(self, building_id: str, name: str, building_type: str, *args, **kwargs):
        super().__init__(building_id, name, *args, **kwargs)
        self.building_type = building_type
        self.status: str = "unknown"
        self.inventory: Dict[str, int] = {}
        self.metadata: Dict[str, Any] = {}

    def get_status(self) -> str:
        return self.status

    def get_inventory(self) -> Dict[str, int]:
        return self.inventory

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
