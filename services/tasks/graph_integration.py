"""
Integration layer between the fluid dynamics priority system and existing graph structures.

This module provides utilities to convert production/inventory graphs into task graphs
for priority calculation, and to apply priority-based scheduling.
"""
import networkx as nx
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime

from .task import Task, TaskStatus
from .fluid_priority import FluidDynamicsPriorityCalculator


class GraphTaskIntegrator:
    """
    Integrates the fluid dynamics priority system with existing NetworkX-based graphs.
    
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
        self.node_to_task_map: Dict[str, str] = {}  # Maps graph node IDs to task IDs
        self.task_to_node_map: Dict[str, str] = {}  # Maps task IDs to graph node IDs
    
    def create_tasks_from_production_graph(self, production_graph, base_priority_map: Optional[Dict[str, float]] = None) -> List[Task]:
        """
        Convert a production graph into tasks for priority calculation.
        
        Args:
            production_graph: NetworkX DiGraph representing production dependencies
            base_priority_map: Optional mapping of node names to base priorities
            
        Returns:
            List of created Task objects
        """
        if base_priority_map is None:
            base_priority_map = {}
        
        created_tasks = []
        
        # Create tasks for each node in the graph
        for node_id in production_graph.nodes():
            node_data = production_graph.nodes[node_id]
            node_obj = node_data.get('node')
            
            # Determine task properties
            task_id = f"prod_{node_id}"
            if node_obj:
                name = getattr(node_obj, 'name', node_id)
                category = getattr(node_obj, 'category', 'production')
                task_type = f"{category}_production"
            else:
                name = node_id
                task_type = "production"
            
            # Get base priority from map or use category-based defaults
            base_priority = base_priority_map.get(node_id, self._get_default_priority_by_type(task_type))
            
            # Create the task
            task = Task(
                task_id=task_id,
                name=name,
                task_type=task_type,
                base_priority=base_priority
            )
            
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
        
        return created_tasks
    
    def create_tasks_from_inventory_graph(self, inventory_graph, base_priority_map: Optional[Dict[str, float]] = None) -> List[Task]:
        """
        Convert an inventory graph into tasks for priority calculation.
        
        Args:
            inventory_graph: InventoryGraph object with nodes and edges
            base_priority_map: Optional mapping of node IDs to base priorities
            
        Returns:
            List of created Task objects
        """
        if base_priority_map is None:
            base_priority_map = {}
        
        created_tasks = []
        
        # Create tasks for each inventory node
        for node_id, inventory_node in inventory_graph.nodes.items():
            # Create transport/supply tasks based on inventory status
            task_id = f"supply_{node_id}"
            name = f"Supply {inventory_node.location_name}"
            
            # Determine priority based on inventory status and delta
            base_priority = base_priority_map.get(node_id, self._get_priority_from_inventory_status(inventory_node))
            
            task = Task(
                task_id=task_id,
                name=name,
                task_type="supply",
                base_priority=base_priority
            )
            
            # Check if task should be blocked based on inventory status
            if inventory_node.status in ["critical", "blocked"]:
                task.mark_blocked()
            
            # Map relationships
            self.node_to_task_map[node_id] = task_id
            self.task_to_node_map[task_id] = node_id
            
            created_tasks.append(task)
            self.priority_calc.add_task(task)
        
        # Set up dependencies based on edges (supply chains)
        for node_id, inventory_node in inventory_graph.nodes.items():
            source_task_id = self.node_to_task_map[node_id]
            
            for edge in inventory_node.edges:
                target_node_id = edge.target.node_id
                if target_node_id in self.node_to_task_map:
                    target_task_id = self.node_to_task_map[target_node_id]
                    
                    source_task = self.priority_calc.get_task(source_task_id)
                    target_task = self.priority_calc.get_task(target_task_id)
                    
                    if source_task and target_task:
                        # Target depends on source for supplies
                        target_task.upstream_dependencies.add(source_task_id)
                        source_task.downstream_dependents.add(target_task_id)
        
        return created_tasks
    
    def mark_production_blocked(self, node_id: str, reason: str = "") -> bool:
        """
        Mark a production node as blocked, which will affect priority calculations.
        
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
        """
        Mark a production node as unblocked.
        
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
        """
        Generate a detailed priority report for the integrated system.
        
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
        report.append("")
        
        report.append("TOP PRIORITY RECOMMENDATIONS:")
        report.append("-" * 50)
        report.append(f"{'Rank':<5} {'Node ID':<15} {'Priority':<10} {'Blocked Tasks':<15} {'Status'}")
        report.append("-" * 70)
        
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
        
        for node_id, name, dependent_count, blocked_hours in critical_bottlenecks[:5]:
            report.append(f"- {node_id}: {name}")
            report.append(f"  Blocking {dependent_count} downstream tasks for {blocked_hours:.1f} hours")
        
        if not critical_bottlenecks:
            report.append("No critical bottlenecks detected.")
        
        return "\n".join(report)
    
    def _get_default_priority_by_type(self, task_type: str) -> float:
        """Get default priority based on task type."""
        priority_map = {
            "resource_production": 1.0,
            "refined_production": 2.0,
            "material_production": 3.0,
            "product_production": 4.0,
            "transport": 3.0,
            "supply": 2.5
        }
        return priority_map.get(task_type, 1.0)
    
    def _get_priority_from_inventory_status(self, inventory_node) -> float:
        """Calculate priority based on inventory node status and delta."""
        base_priority = 2.0
        
        # Increase priority based on status
        status_multipliers = {
            "critical": 3.0,
            "low": 2.0,
            "ok": 1.0,
            "blocked": 2.5
        }
        
        multiplier = status_multipliers.get(inventory_node.status, 1.0)
        
        # Increase priority if there's high demand (negative delta)
        total_demand = sum(abs(qty) for qty in inventory_node.delta.values() if qty < 0)
        demand_bonus = min(total_demand * 0.1, 2.0)  # Cap at +2.0
        
        return base_priority * multiplier + demand_bonus