from typing import Any

from services.inventory.inventory_graph import InventoryNode
from services.inventory.production_nodes import BaseType


class Priority:
    def __init__(self, signals: dict[str, float], weights: dict[str, float] = None):
        self.signals = signals
        self.weights = weights or self.default_weights()
        self.score = self.compute_score()

    def default_weights(self) -> dict[str, float]:
        # Example weights; adjust as needed for your domain
        return {
            "delta": 1.0,           # Unmet demand
            "inventory": -0.5,      # Surplus inventory (negative weight)
            "status": 2.0,          # Node status (critical=2, low=1, ok=0)
            "distance": -0.2,       # Distance to fulfill (negative weight)
            # Add more signals as needed
        }

    def compute_score(self) -> float:
        score = 0.0
        for signal, value in self.signals.items():
            weight = self.weights.get(signal, 0.0)
            score += weight * value
        return score

    def __repr__(self):
        # Use print parameters and round for formatting
        return "<Priority score=" + str(round(self.score, 2)) + " signals=" + str(self.signals) + ">"

class Task:
    def __init__(self, task_type: str, node: InventoryNode, item: str, quantity: int, details: dict[str, Any] = None, priority: "Priority" = None):
        self.task_type = task_type  # 'transportation' or 'production'
        self.node = node
        self.item = item
        self.quantity = quantity
        self.details = details or {}
        self.priority = priority

    def __repr__(self):
        # Use print parameters and round for formatting
        priority_score = self.priority.score if self.priority else "N/A"
        if isinstance(priority_score, float):
            priority_score = round(priority_score, 2)
        print("<Task type=", self.task_type, "node=", self.node.location_name, "item=", self.item, "qty=", self.quantity, "priority=", priority_score, ">")
        return ""

class TransportationTask(Task):
    def __init__(self, source: InventoryNode, destination: InventoryNode, item: str, quantity: int, signals: dict[str, float]):
        priority = Priority(signals)
        super().__init__("transportation", destination, item, quantity, details={"source": source}, priority=priority)
        self.source = source
        self.destination = destination

class ProductionTask(Task):
    def __init__(self, node: InventoryNode, item: str, quantity: int, signals: dict[str, float]):
        priority = Priority(signals)
        super().__init__("production", node, item, quantity, priority=priority)

class TaskGenerator:
    def __init__(self, nodes: list[InventoryNode]):
        self.nodes = nodes

    def get_actionable_tasks(self) -> list[Task]:
        tasks: list[Task] = []
        for node in self.nodes:
            for item, delta in node.delta.items():
                if delta > 0:
                    # Transportation: Find upstream nodes with surplus
                    for edge in node.edges:
                        if isinstance(edge, InventoryNode) and edge.inventory.get(item, 0) > 0:
                            qty = min(edge.inventory[item], delta)
                            signals = {
                                "delta": delta,
                                "inventory": edge.inventory.get(item, 0),
                                "status": self.status_to_signal(node.status),
                                # 'distance': self.compute_distance(edge, node), # Placeholder for future
                            }
                            tasks.append(TransportationTask(source=edge, destination=node, item=item, quantity=qty, signals=signals))
                    # Production: If node can produce the item
                    if node.base_type in [BaseType.PRODUCTION, BaseType.FACILITY]:
                        signals = {
                            "delta": delta,
                            "inventory": node.inventory.get(item, 0),
                            "status": self.status_to_signal(node.status),
                        }
                        tasks.append(ProductionTask(node=node, item=item, quantity=delta, signals=signals))
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
