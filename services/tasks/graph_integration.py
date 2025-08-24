"""Integration layer between the fluid dynamics priority system and existing graph structures.

This module provides utilities to convert production/inventory graphs into task graphs,
for priority calculation, and to apply priority-based scheduling.
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from .fluid_priority import FluidDynamicsPriorityCalculator
from .task import Task, TaskStatus


class GraphTaskIntegrator:
    """Integrates the fluid dynamics priority system with existing NetworkX-based graphs.

    This class can convert production chains and inventory networks into task graphs,
    apply priority calculations, and provide scheduling recommendations.
    """
    
    def __init__(self, priority_calculator: Optional[FluidDynamicsPriorityCalculator] = None):
        """
        Initialize the integrator.
        
        Args:
            priority_calculator: Optional custom calculator, creates default if None

        """
        self.priority_calc = priority_calculator or FluidDynamicsPriorityCalculator()
        self.node_to_task_map: dict[str, str] = {}  # Maps graph node IDs to task IDs
        self.task_to_node_map: dict[str, str] = {}  # Maps task IDs to graph node IDs

    def create_tasks_from_production_graph(
        self,
        production_graph,
        base_priority_map: Optional[Dict[str, float]] = None
    ) -> List[Task]:
        """
        Convert a production graph into tasks for priority calculation.

        Args:
            production_graph: NetworkX DiGraph representing production dependencies.
            base_priority_map: Optional mapping of node names to base priorities.

        Returns:
            List of created Task objects

        """
        if base_priority_map is None:
            if base_priority_map is None:
                base_priority_map = {}

            created_tasks = []

            # Create tasks for each edge in the inventory graph
            for edge in getattr(inventory_graph, 'edges', []):
                source = getattr(edge, 'source', None)
                target = getattr(edge, 'target', None)
                source_id = getattr(source, 'node_id', "unknown") if source else "unknown"
                target_id = getattr(target, 'node_id', "unknown") if target else "unknown"
                edge_key = f"{source_id}->{target_id}"
                source_name = getattr(source, 'location_name', str(source_id)) if source else str(source_id)
                target_name = getattr(target, 'location_name', str(target_id)) if target else str(target_id)
                name = f"Supply from {source_name} to {target_name}"
                # Priority can be based on source inventory status, target needs, or edge/order properties
                source_status = getattr(source, 'status', None)
                target_status = getattr(target, 'status', None)
                # Use a simple priority function for now
                base_priority = base_priority_map.get(edge_key, 5.0)
                # Autogenerate task_id unless a unique custom ID is required
                custom_task_id = f"supply_{source_id}_to_{target_id}"
                # Collision detection for custom IDs
                if custom_task_id in self.task_to_node_map:
                    import uuid
                    custom_task_id = f"{custom_task_id}_{uuid.uuid4()}"
                task = Task(
                    task_id=custom_task_id,
                    name=name,
                    task_type="supply_edge",
                    base_priority=base_priority
                )
                # Blocked if source or target is critical/blocked
                if source_status in ["critical", "blocked"] or target_status in ["critical", "blocked"]:
                    task.mark_blocked()
                # Map relationships
                self.node_to_task_map[edge_key] = custom_task_id
                self.task_to_node_map[custom_task_id] = edge_key
                created_tasks.append(task)
                self.priority_calc.add_task(task)

            # Edge-tasks are independent unless a more complex supply chain is modeled
            return created_tasks
            # Map relationships for later dependency setup
            self.node_to_task_map[node_id] = task_id
            self.task_to_node_map[task_id] = node_id

            created_tasks.append(task)
            self.priority_calc.add_task(task)

        # Set up dependencies based on graph edges
        for source, target in production_graph.edges():
            source_task_id = self.node_to_task_map[source]
            target_task_id = self.node_to_task_map[target]

            source_task = self.priority_calc.get_task(source_task_id)
            target_task = self.priority_calc.get_task(target_task_id)

            if source_task and target_task:
                # In production graphs, source provides input to target
                target_task.upstream_dependencies.add(source_task_id)
                source_task.downstream_dependents.add(target_task_id)
        
        created_tasks = []
        # Create tasks for each edge in the inventory graph
        for node_id, inventory_node in inventory_graph.nodes.items():
            for edge in inventory_node.edges:
                source_id = node_id
                target_id = edge.target.node_id
                edge_key = (source_id, target_id)
                task_id = f"supply_{source_id}_to_{target_id}"
                name = f"Supply from {inventory_node.location_name} to {edge.target.location_name}"
                # Priority can be based on source inventory status, target needs, or edge/order properties
                base_priority = base_priority_map.get(edge_key, self._get_priority_from_inventory_status(inventory_node))
                task = Task(
                    task_id=task_id,
                    name=name,
                    task_type="supply_edge",
                    base_priority=base_priority
                )
                # Blocked if source or target is critical/blocked
                if inventory_node.status in ["critical", "blocked"] or getattr(edge.target, "status", None) in ["critical", "blocked"]:
                    task.mark_blocked()
                # Map relationships
                self.node_to_task_map[edge_key] = task_id
                self.task_to_node_map[task_id] = edge_key
                created_tasks.append(task)
                self.priority_calc.add_task(task)
        # Dependencies between edge-tasks can be set up if needed (e.g., chained supply routes)
        # For now, edge-tasks are independent unless a more complex supply chain is modeled
        return created_tasks

    def mark_production_blocked(self, node_id: str, reason: str = "") -> bool:
        """Mark a production node as blocked, which will affect priority calculations.
        
        Args:
            node_id: ID of the production node to mark as blocked
            reason: Optional reason for the blockage
            
        Returns:
            True if task was found and marked blocked, False otherwise

        """
        task_id = self.node_to_task_map.get(node_id)
        if not task_id:
            return False

        task = self.priority_calc.get_task(task_id)
        if not task:
            return False

        task.mark_blocked()
        if reason:
            task.metadata["block_reason"] = reason

        return True

    def mark_production_unblocked(self, node_id: str) -> bool:
        """Mark a production node as unblocked.
        
        Args:
            node_id: ID of the production node to unblock
            
        Returns:
            True if task was found and unblocked, False otherwise

        """
        task_id = self.node_to_task_map.get(node_id)
        if not task_id:
            return False

        task = self.priority_calc.get_task(task_id)
        if not task:
            return False

        task.mark_unblocked()
        task.metadata.pop("block_reason", None)

        return True
    
    def get_priority_recommendations(self, top_n: int = 10) -> List[Tuple[str, str, float, Dict[str, Any]]]:
        """
        Get priority-ordered recommendations for which production/supply tasks to focus on.
        
        Args:
            top_n: Number of top priority recommendations to return
            
        Returns:
            List of (node_id, task_name, priority_score, details) tuples

        """
        rankings = self.priority_calc.get_priority_rankings()
        recommendations = []

        for task_id, priority, details in rankings[:top_n]:
            node_id = self.task_to_node_map.get(task_id, "unknown")
            task = self.priority_calc.get_task(task_id)
            task_name = task.name if task else task_id

            recommendations.append((node_id, task_name, priority, details))

        return recommendations

    def generate_priority_report(self) -> str:
        """Generate a detailed priority report for the integrated system.
        
        Returns:
            Formatted string report of current priorities and recommendations

        """
        recommendations = self.get_priority_recommendations(15)

        report = []
        report.append("FLUID DYNAMICS PRIORITY REPORT")
        report.append("=" * 50)
        report.append(f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        report.append(f"Total tasks analyzed: {len(self.priority_calc.task_graph)}")
        
        # Count blocked tasks
        blocked_count = sum(1 for task in self.priority_calc.task_graph.values() 
                          if task.status == TaskStatus.BLOCKED)
        report.append(f"Currently blocked tasks: {blocked_count}")
        
        for i, (node_id, task_name, priority, details) in enumerate(recommendations):
            task_id = self.node_to_task_map.get(node_id, "")
            task = self.priority_calc.get_task(task_id) if task_id else None
            status = task.status.value if task else "unknown"
            blocked_count = details.get("blocked_count", 0)
            
            report.append(f"{i+1:<5} {node_id:<15} {priority:<10.2f} {blocked_count:<15} {status}")
        
        report.append("")
        report.append("CRITICAL BOTTLENECKS:")
        report.append("-" * 30)
        
        # Find tasks with most downstream dependencies
        critical_bottlenecks = []
        for task_id, task in self.priority_calc.task_graph.items():
            if task.status == TaskStatus.BLOCKED and len(task.downstream_dependents) > 0:
                node_id = self.task_to_node_map.get(task_id, task_id)
                critical_bottlenecks.append((node_id, task.name, len(task.downstream_dependents), 
                                           task.get_blocked_duration_hours()))

        # Sort by number of dependents
        critical_bottlenecks.sort(key=lambda x: x[2], reverse=True)

        report.append("")
        report.append("CRITICAL BOTTLENECKS:")

        for node_id, name, dependent_count, blocked_hours in critical_bottlenecks[:5]:
            report.append("- {}: {}".format(node_id, name))
            report.append("  Blocking {} downstream tasks for {} hours".format(dependent_count, round(blocked_hours, 1)))

        if not critical_bottlenecks:
            report.append("No critical bottlenecks detected.")

        return "\n".join(report)
    
    def _get_default_priority_by_type(self, item_or_type: str) -> float:
        """Get default priority based on production type or item name.

        This is a placeholder for future item-specific tuning.
        BMATs and shirts are highest priority, followed by other essentials.
        """
        item_priority_table = {
            "Basic Materials": 10.0,  # BMATs
            "Shirts": 9.5,
            "Refined Materials": 8.0,  # RMATs
            "Soldier's Supplies": 7.5,
            "Bandages": 7.0,
            "7.62 mm Ammo": 6.5,
            "Blakerow Rifle": 6.0,
            # Add more items as needed
        }
        # Default fallback priority for unknown items
        return item_priority_table.get(item_or_type, 5.0)
    
