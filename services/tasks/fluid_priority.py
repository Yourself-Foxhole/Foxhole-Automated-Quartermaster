"""
Fluid Dynamics Priority Algorithm

This module implements a priority calculation system based on the analogy of fluid dynamics
and water pressure behind a dam. The more blocked tasks "build up" behind a bottleneck,
the higher the priority becomes.
"""
import math

from typing import Optional, List, Dict, Tuple

from .task import Task, TaskStatus


class FluidDynamicsPriorityCalculator:
    # NOTE: base_priority for each task should be set using the signal-weight system from task_layer.py
    # (signals: delta, inventory, status, distance; weights: delta=1.0, inventory=-0.5, status=2.0, distance=-0.2)
    # This ensures consistency and avoids conflicting priority logic between modules.
    """
    Calculates task priority based on fluid dynamics principles.
    
    The algorithm works like water building pressure behind a dam:
    1. Count blocked upstream tasks (water volume)
    2. Sum their relative weights (water density)
    3. Apply time-based multipliers (pressure buildup over time)
    4. Calculate final priority score (water pressure)
    """
    
    def __init__(self, 
                 time_pressure_factor: float = 0.035,
                 max_time_multiplier: float = 5.0,
                 base_priority_weight: float = 1.0,
                 additional_algorithms: Optional[List] = None):
        """Initialize the priority calculator.

        Args:
            time_pressure_factor: Blocked time effect per hour (5 days to max)
            max_time_multiplier: Max time pressure multiplier
            base_priority_weight: Default priority weight
            additional_algorithms: List of other priority algorithms for weighted average
        """
        self.time_pressure_factor = time_pressure_factor
        self.max_time_multiplier = max_time_multiplier
        self.base_priority_weight = base_priority_weight
        self.task_graph: Dict[str, Task] = {}
        self.additional_algorithms = additional_algorithms or []
    
    def add_task(self, task) -> None:
        """Add a task to the priority calculation system. Accepts Task, ProductionTask, or TransportationTask."""
        # Support both new and legacy task types
        if hasattr(task, 'task_id'):
            key = getattr(task, 'task_id')
        elif hasattr(task, 'item') and hasattr(task, 'node'):
            # Use item+node as fallback unique key for legacy tasks
            key = f"{getattr(task, 'item', '')}_{getattr(task, 'node', None)}"
        else:
            key = str(id(task))
        self.task_graph[key] = task
    
    def remove_task(self, task_id: str) -> None:
        """Remove a task from the system."""
        if task_id in self.task_graph:
            del self.task_graph[task_id]
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.task_graph.get(task_id)
    
    def find_upstream_blocked_tasks(
        self, task_id: str, visited: None | set[str] = None
    ) -> list[Task]:
        """
        Find all blocked tasks upstream from the given task.
        
        This traverses the dependency graph to find tasks that are blocked
        and preventing the given task from proceeding.
        
        Args:
            task_id: The task to analyze
            visited: Set of already visited tasks (to prevent cycles)
            
        Returns:
            List of blocked upstream tasks
        """
        if visited is None:
            visited = set()
        if task_id in visited or task_id not in self.task_graph:
            return []
        
        visited.add(task_id)
        task = self.task_graph[task_id]
        blocked_tasks = []
        
        # If this task is blocked, include it
        if task.status == TaskStatus.BLOCKED:
            blocked_tasks.append(task)
        
        # Recursively check upstream dependencies
        for dep_id in task.upstream_dependencies:
            blocked_tasks.extend(
                self.find_upstream_blocked_tasks(dep_id, visited.copy())
            )
        return blocked_tasks
    
    def calculate_time_pressure_multiplier(
        self, blocked_duration_hours: float
    ) -> float:
        """
        Calculate time-based pressure multiplier.
        
        Uses an exponential growth function to simulate increasing pressure
        over time, capped at max_time_multiplier.
        
        Args:
            blocked_duration_hours: How long the task has been blocked
            
        Returns:
            Time pressure multiplier (1.0 to max_time_multiplier)
        """
        if blocked_duration_hours <= 0:
            return 1.0
        
        # Exponential growth: 1 + factor * (e^(hours * factor) - 1)
        time_multiplier = 1.0 + (
            math.exp(blocked_duration_hours * self.time_pressure_factor) - 1.0
        )
        return min(time_multiplier, self.max_time_multiplier)
    
    def calculate_fluid_pressure(self, task_id: str) -> Tuple[float, Dict[str, any]]:
        """
        Calculate the fluid dynamics priority for a task.
        
        This is the main algorithm that computes priority based on:
        1. Number of blocked upstream tasks (volume)
        2. Sum of their priority weights (density)
        3. Time-based pressure buildup (pressure over time)
        
        Args:
            task_id: The task to calculate priority for
            
        Returns:
            Tuple of (priority_score, calculation_details)
        """
        if task_id not in self.task_graph:
            return 0.0, {"error": "Task not found"}
        
        task = self.task_graph[task_id]
        
        # Find all blocked upstream tasks
        blocked_upstream = self.find_upstream_blocked_tasks(task_id)
        
        if not blocked_upstream:
            base_priority = task.base_priority
            # Weighted average stub: add other algorithms if present
            if self.additional_algorithms:
                weighted_sum = base_priority
                total_weight = 1.0
                for algo, weight in self.additional_algorithms:
                    weighted_sum += algo(task_id) * weight
                    total_weight += weight
                base_priority = weighted_sum / total_weight
            return base_priority, {
                "blocked_count": 0,
                "total_weight": base_priority,
                "time_multiplier": 1.0,
                "blocked_tasks": []
            }
        
        # Calculate total "water volume" (sum of blocked task weights)
        total_blocked_weight = 0.0
        task_details = []
        max_blocked_duration = 0.0
        
        for blocked_task in blocked_upstream:
            weight = blocked_task.base_priority
            duration = blocked_task.get_blocked_duration_hours()
            total_blocked_weight += weight
            max_blocked_duration = max(max_blocked_duration, duration)
            
            task_details.append({
                "task_id": blocked_task.task_id,
                "name": blocked_task.name,
                "weight": weight,
                "blocked_hours": duration
            })
        
        # Calculate time pressure multiplier based on longest blocked task
        time_multiplier = self.calculate_time_pressure_multiplier(max_blocked_duration)
        
        # Final priority = blocked_weight * time_pressure + base_priority
        priority_score = (total_blocked_weight * time_multiplier) + task.base_priority
        # Weighted average stub: add other algorithms if present
        if self.additional_algorithms:
            weighted_sum = priority_score
            total_weight = 1.0
            for algo, weight in self.additional_algorithms:
                weighted_sum += algo(task_id) * weight
                total_weight += weight
            priority_score = weighted_sum / total_weight
        
        calculation_details = {
            "blocked_count": len(blocked_upstream),
            "total_weight": total_blocked_weight,
            "time_multiplier": time_multiplier,
            "max_blocked_hours": max_blocked_duration,
            "base_priority": task.base_priority,
            "blocked_tasks": task_details,
            "formula": f"({total_blocked_weight:.2f} * {time_multiplier:.2f}) + {task.base_priority:.2f}"
        }
        
        return priority_score, calculation_details
    
    def get_priority_rankings(self, task_ids: Optional[List[str]] = None) -> List[Tuple[str, float, Dict[str, any]]]:
        """
        Get priority rankings for all tasks or a subset of tasks.
        
        Args:
            task_ids: Optional list of specific task IDs to rank
            
        Returns:
            List of (task_id, priority_score, details) sorted by priority (highest first)
        """
        if task_ids is None:
            task_ids = list(self.task_graph.keys())
        
        rankings = []
        for task_id in task_ids:
            priority, details = self.calculate_fluid_pressure(task_id)
            rankings.append((task_id, priority, details))
        
        # Sort by priority score (highest first)
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings
    
    def print_priority_analysis(self, task_id: str) -> None:
        """Print a detailed analysis of priority calculation for a task."""
        priority, details = self.calculate_fluid_pressure(task_id)
        task = self.task_graph.get(task_id)
        
        if not task:
            print(f"Task {task_id} not found")
            return
        
        print(f"\n=== Fluid Dynamics Priority Analysis ===")
        print(f"Task: {task.name} ({task_id})")
        print(f"Status: {task.status.value}")
        print(f"Final Priority Score: {priority:.2f}")
        print(f"\nCalculation Details:")
        print(f"  Base Priority: {details.get('base_priority', 0):.2f}")
        print(f"  Blocked Tasks Count: {details.get('blocked_count', 0)}")
        print(f"  Total Blocked Weight: {details.get('total_weight', 0):.2f}")
        print(f"  Time Multiplier: {details.get('time_multiplier', 1):.2f}")
        print(f"  Max Blocked Duration: {details.get('max_blocked_hours', 0):.1f} hours")
        print(f"  Formula: {details.get('formula', 'N/A')}")
        
        if details.get('blocked_tasks'):
            print(f"\nBlocked Upstream Tasks:")
            for bt in details['blocked_tasks']:
                print(f"  - {bt['name']} ({bt['task_id']}): weight={bt['weight']:.2f}, blocked={bt['blocked_hours']:.1f}h")
        print("=" * 40)