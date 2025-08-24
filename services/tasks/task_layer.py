from typing import Any
from datetime import datetime, timezone

from services.inventory.inventory_graph import InventoryNode
from services.inventory.production_nodes import BaseType

# Import the fluid dynamics priority calculator
from .fluid_priority import FluidDynamicsPriorityCalculator
from .task import TaskStatus


class Priority:
    def __init__(self, signals: dict[str, float], weights: dict[str, float] = None, fluid_calc: FluidDynamicsPriorityCalculator = None, task_id: str = None):
        self.signals = signals
        self.weights = weights or self.default_weights()
        self.fluid_calc = fluid_calc
        self.task_id = task_id
        self.score = self.compute_score()

    def default_weights(self) -> dict[str, float]:
        # Example weights; adjust as needed for your domain
        return {
            "delta": 1.0,                   # Unmet demand
            "inventory": -0.5,              # Surplus inventory (negative weight)
            "status": 2.0,                  # Node status (critical=2, low=1, ok=0)
            "distance": -0.2,               # Distance to fulfill (negative weight)
            "transport_time": -0.3,         # Transportation time (negative weight - shorter is better)
            "fluid_dynamics": 1.5,          # Fluid dynamics priority signal
            # Add more signals as needed
        }

    def compute_score(self) -> float:
        score = 0.0
        for signal, value in self.signals.items():
            weight = self.weights.get(signal, 0.0)
            score += weight * value
        
        # Add fluid dynamics priority if available
        if self.fluid_calc and self.task_id:
            try:
                fluid_priority, _ = self.fluid_calc.calculate_fluid_pressure(self.task_id)
                weight = self.weights.get("fluid_dynamics", 0.0)
                score += weight * fluid_priority
            except:
                # If fluid dynamics calculation fails, continue without it
                pass
                
        return score

    def __repr__(self):
        # Use print parameters and round for formatting
        return "<Priority score=" + str(round(self.score, 2)) + " signals=" + str(self.signals) + ">"

class Task:
    def __init__(self, task_type: str, node: InventoryNode, item: str, quantity: int, details: dict[str, Any] = None, priority: "Priority" = None, task_id: str = None):
        self.task_type = task_type  # "transportation" or "production"
        self.node = node
        self.item = item
        self.quantity = quantity
        self.details = details or {}
        self.priority = priority
        self.task_id = task_id or self._generate_unique_id()
        self.status = TaskStatus.PENDING
        self.blocked_since: datetime | None = None
        self.upstream_dependencies: set[str] = set()
        self.downstream_dependents: set[str] = set()
        
    @staticmethod 
    def _generate_unique_id() -> str:
        """Generate a unique task ID."""
        import uuid
        return str(uuid.uuid4())
        
    def mark_blocked(self, reason: str = None) -> None:
        """Mark this task as blocked and record the time."""
        if self.status != TaskStatus.BLOCKED:
            self.status = TaskStatus.BLOCKED
            self.blocked_since = datetime.now(timezone.utc)
            if reason:
                self.details["block_reason"] = reason
    
    def mark_unblocked(self) -> None:
        """Mark this task as no longer blocked."""
        if self.status == TaskStatus.BLOCKED:
            self.status = TaskStatus.PENDING
            self.blocked_since = None
            if "block_reason" in self.details:
                del self.details["block_reason"]
    
    def get_blocked_duration_hours(self) -> float:
        """Get how long this task has been blocked in hours."""
        if self.blocked_since is None:
            return 0.0
        return (datetime.now(timezone.utc) - self.blocked_since).total_seconds() / 3600.0

    def __repr__(self):
        # Use print parameters and round for formatting
        priority_score = self.priority.score if self.priority else "N/A"
        if isinstance(priority_score, float):
            priority_score = round(priority_score, 2)
        print("<Task type=", self.task_type, "node=", self.node.location_name, "item=", self.item, "qty=", self.quantity, "priority=", priority_score, ">")
        return ""

class TransportationTask(Task):
    def __init__(self, source: InventoryNode, destination: InventoryNode, item: str, quantity: int, signals: dict[str, float], fluid_calc: FluidDynamicsPriorityCalculator = None):
        task_id = self._generate_unique_id()
        priority = Priority(signals, fluid_calc=fluid_calc, task_id=task_id)
        super().__init__("transportation", destination, item, quantity, details={"source": source}, priority=priority, task_id=task_id)
        self.source = source
        self.destination = destination
        
    @staticmethod 
    def _generate_unique_id() -> str:
        """Generate a unique task ID."""
        import uuid
        return str(uuid.uuid4())

class ProductionTask(Task):
    def __init__(self, node: InventoryNode, item: str, quantity: int, signals: dict[str, float], fluid_calc: FluidDynamicsPriorityCalculator = None):
        task_id = self._generate_unique_id()
        priority = Priority(signals, fluid_calc=fluid_calc, task_id=task_id)
        super().__init__("production", node, item, quantity, priority=priority, task_id=task_id)
        
    @staticmethod 
    def _generate_unique_id() -> str:
        """Generate a unique task ID."""
        import uuid
        return str(uuid.uuid4())

class TaskGenerator:
    def __init__(self, nodes: list[InventoryNode], fluid_calc: FluidDynamicsPriorityCalculator = None):
        self.nodes = nodes
        self.fluid_calc = fluid_calc or FluidDynamicsPriorityCalculator()

    def get_actionable_tasks(self) -> list[Task]:
        tasks: list[Task] = []
        for node in self.nodes:
            for item, delta in node.delta.items():
                if delta > 0:
                    # Transportation: Find upstream nodes with surplus
                    for edge in node.edges:
                        source_node = getattr(edge, 'source', None)
                        if source_node and hasattr(source_node, 'inventory') and source_node.inventory.get(item, 0) > 0:
                            qty = min(source_node.inventory[item], delta)
                            signals = {
                                "delta": delta,
                                "inventory": source_node.inventory.get(item, 0),
                                "status": self.status_to_signal(node.status),
                                # "distance": self.compute_distance(source_node, node), # Placeholder for future
                            }
                            # Add transport_time signal if available
                            if edge.has_transport_time():
                                signals["transport_time"] = edge.get_transport_time()
                            
                            task = TransportationTask(source=source_node, destination=node, item=item, quantity=qty, signals=signals, fluid_calc=self.fluid_calc)
                            tasks.append(task)
                            # Add task to fluid dynamics calculator for dependency tracking
                            self.fluid_calc.add_task(task)
                    # Production: If node can produce the item
                    if node.base_type in [BaseType.PRODUCTION, BaseType.FACILITY]:
                        signals = {
                            "delta": delta,
                            "inventory": node.inventory.get(item, 0),
                            "status": self.status_to_signal(node.status),
                        }
                        task = ProductionTask(node=node, item=item, quantity=delta, signals=signals, fluid_calc=self.fluid_calc)
                        tasks.append(task)
                        # Add task to fluid dynamics calculator for dependency tracking
                        self.fluid_calc.add_task(task)
        # Sort tasks by descending priority score
        tasks.sort(key=lambda t: t.priority.score if t.priority else 0, reverse=True)
        return tasks

    @staticmethod
    def status_to_signal(status: str) -> float:
        # Map status string to a numeric signal
        mapping = {"critical": 2.0, "low": 1.0, "ok": 0.0, "unknown": 0.0}
        return mapping.get(status, 0.0)

    # Placeholder for future signal computation
    # def compute_distance(self, source: InventoryNode, destination: InventoryNode) -> float:
    #     return 0.0
