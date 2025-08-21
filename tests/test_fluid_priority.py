"""
Tests for the fluid dynamics priority algorithm.
"""
import pytest
from datetime import datetime, timedelta
from services.tasks import Task, TaskStatus, FluidDynamicsPriorityCalculator


class TestTask:
    """Test the Task class functionality."""
    
    def test_task_creation(self):
        """Test basic task creation."""
        task = Task(
            task_id="test_1",
            name="Test Task",
            task_type="production",
            base_priority=2.5
        )
        
        assert task.task_id == "test_1"
        assert task.name == "Test Task"
        assert task.task_type == "production"
        assert task.status == TaskStatus.PENDING
        assert task.base_priority == 2.5
        assert task.blocked_since is None
    
    def test_task_blocking(self):
        """Test task blocking and unblocking."""
        task = Task("test_1", "Test Task", "production")
        
        # Initially not blocked
        assert task.status != TaskStatus.BLOCKED
        assert task.blocked_since is None
        assert task.get_blocked_duration_hours() == 0.0
        
        # Block the task
        before_block = datetime.utcnow()
        task.mark_blocked()
        after_block = datetime.utcnow()
        
        assert task.status == TaskStatus.BLOCKED
        assert task.blocked_since is not None
        assert before_block <= task.blocked_since <= after_block
        assert task.get_blocked_duration_hours() >= 0.0
        
        # Unblock the task
        task.mark_unblocked()
        assert task.status == TaskStatus.PENDING
        assert task.blocked_since is None
        assert task.get_blocked_duration_hours() == 0.0
    
    def test_task_dependencies(self):
        """Test task dependency management."""
        task = Task("test_1", "Test Task", "production")
        task.upstream_dependencies.add("dep_1")
        task.upstream_dependencies.add("dep_2")
        task.downstream_dependents.add("dependent_1")
        
        assert "dep_1" in task.upstream_dependencies
        assert "dep_2" in task.upstream_dependencies
        assert "dependent_1" in task.downstream_dependents


class TestFluidDynamicsPriorityCalculator:
    """Test the fluid dynamics priority calculator."""
    
    def test_calculator_initialization(self):
        """Test calculator initialization with default values."""
        calc = FluidDynamicsPriorityCalculator()
        
        assert calc.time_pressure_factor == 0.1
        assert calc.max_time_multiplier == 5.0
        assert calc.base_priority_weight == 1.0
        assert len(calc.task_graph) == 0
    
    def test_calculator_custom_initialization(self):
        """Test calculator initialization with custom values."""
        calc = FluidDynamicsPriorityCalculator(
            time_pressure_factor=0.2,
            max_time_multiplier=10.0,
            base_priority_weight=2.0
        )
        
        assert calc.time_pressure_factor == 0.2
        assert calc.max_time_multiplier == 10.0
        assert calc.base_priority_weight == 2.0
    
    def test_add_remove_tasks(self):
        """Test adding and removing tasks."""
        calc = FluidDynamicsPriorityCalculator()
        task = Task("test_1", "Test Task", "production")
        
        # Add task
        calc.add_task(task)
        assert "test_1" in calc.task_graph
        assert calc.get_task("test_1") == task
        
        # Remove task
        calc.remove_task("test_1")
        assert "test_1" not in calc.task_graph
        assert calc.get_task("test_1") is None
    
    def test_time_pressure_multiplier(self):
        """Test time pressure multiplier calculation."""
        calc = FluidDynamicsPriorityCalculator(time_pressure_factor=0.1, max_time_multiplier=5.0)
        
        # No blocked time = 1.0 multiplier
        assert calc.calculate_time_pressure_multiplier(0.0) == 1.0
        
        # Some blocked time = > 1.0 multiplier
        multiplier_1h = calc.calculate_time_pressure_multiplier(1.0)
        assert multiplier_1h > 1.0
        
        # More blocked time = higher multiplier
        multiplier_5h = calc.calculate_time_pressure_multiplier(5.0)
        assert multiplier_5h > multiplier_1h
        
        # Very long blocked time should be capped
        multiplier_100h = calc.calculate_time_pressure_multiplier(100.0)
        assert multiplier_100h == 5.0
    
    def test_simple_priority_calculation(self):
        """Test priority calculation for a task with no blocked dependencies."""
        calc = FluidDynamicsPriorityCalculator()
        task = Task("test_1", "Test Task", "production", base_priority=3.0)
        calc.add_task(task)
        
        priority, details = calc.calculate_fluid_pressure("test_1")
        
        # With no blocked dependencies, priority should equal base priority
        assert priority == 3.0
        assert details["blocked_count"] == 0
        assert details["total_weight"] == 3.0
        assert details["time_multiplier"] == 1.0
        assert details["blocked_tasks"] == []
    
    def test_single_blocked_dependency(self):
        """Test priority calculation with one blocked upstream task."""
        calc = FluidDynamicsPriorityCalculator()
        
        # Create dependency chain: blocked_task -> test_task
        blocked_task = Task("blocked_1", "Blocked Task", "production", base_priority=2.0)
        blocked_task.mark_blocked()
        
        test_task = Task("test_1", "Test Task", "production", base_priority=1.0)
        test_task.upstream_dependencies.add("blocked_1")
        
        calc.add_task(blocked_task)
        calc.add_task(test_task)
        
        priority, details = calc.calculate_fluid_pressure("test_1")
        
        # Priority should be: blocked_weight * time_multiplier + base_priority
        # = 2.0 * ~1.0 + 1.0 = ~3.0
        assert priority > 1.0  # Higher than base priority
        assert details["blocked_count"] == 1
        assert details["total_weight"] == 2.0
        assert details["base_priority"] == 1.0
        assert len(details["blocked_tasks"]) == 1
        assert details["blocked_tasks"][0]["task_id"] == "blocked_1"
    
    def test_multiple_blocked_dependencies(self):
        """Test priority calculation with multiple blocked upstream tasks."""
        calc = FluidDynamicsPriorityCalculator()
        
        # Create dependency chain: blocked_1, blocked_2 -> test_task
        blocked_1 = Task("blocked_1", "Blocked Task 1", "production", base_priority=2.0)
        blocked_1.mark_blocked()
        
        blocked_2 = Task("blocked_2", "Blocked Task 2", "production", base_priority=3.0)
        blocked_2.mark_blocked()
        
        test_task = Task("test_1", "Test Task", "production", base_priority=1.0)
        test_task.upstream_dependencies.add("blocked_1")
        test_task.upstream_dependencies.add("blocked_2")
        
        calc.add_task(blocked_1)
        calc.add_task(blocked_2)
        calc.add_task(test_task)
        
        priority, details = calc.calculate_fluid_pressure("test_1")
        
        # Priority should include weight from both blocked tasks
        assert details["blocked_count"] == 2
        assert details["total_weight"] == 5.0  # 2.0 + 3.0
        assert len(details["blocked_tasks"]) == 2
        assert priority > 1.0  # Higher than base priority
    
    def test_deep_dependency_chain(self):
        """Test priority calculation with deep blocked dependency chain."""
        calc = FluidDynamicsPriorityCalculator()
        
        # Create chain: blocked_1 -> intermediate -> test_task
        blocked_1 = Task("blocked_1", "Blocked Task 1", "production", base_priority=2.0)
        blocked_1.mark_blocked()
        
        intermediate = Task("intermediate", "Intermediate Task", "production", base_priority=1.5)
        intermediate.upstream_dependencies.add("blocked_1")
        
        test_task = Task("test_1", "Test Task", "production", base_priority=1.0)
        test_task.upstream_dependencies.add("intermediate")
        
        calc.add_task(blocked_1)
        calc.add_task(intermediate)
        calc.add_task(test_task)
        
        priority, details = calc.calculate_fluid_pressure("test_1")
        
        # Should find the blocked task through the chain
        assert details["blocked_count"] == 1
        assert details["total_weight"] == 2.0
        assert details["blocked_tasks"][0]["task_id"] == "blocked_1"
    
    def test_mixed_blocked_unblocked_dependencies(self):
        """Test priority calculation with both blocked and unblocked dependencies."""
        calc = FluidDynamicsPriorityCalculator()
        
        # Create mixed dependencies
        blocked_task = Task("blocked_1", "Blocked Task", "production", base_priority=3.0)
        blocked_task.mark_blocked()
        
        unblocked_task = Task("unblocked_1", "Unblocked Task", "production", base_priority=2.0)
        # Don't block this one
        
        test_task = Task("test_1", "Test Task", "production", base_priority=1.0)
        test_task.upstream_dependencies.add("blocked_1")
        test_task.upstream_dependencies.add("unblocked_1")
        
        calc.add_task(blocked_task)
        calc.add_task(unblocked_task)
        calc.add_task(test_task)
        
        priority, details = calc.calculate_fluid_pressure("test_1")
        
        # Should only count the blocked task
        assert details["blocked_count"] == 1
        assert details["total_weight"] == 3.0
        assert len(details["blocked_tasks"]) == 1
        assert details["blocked_tasks"][0]["task_id"] == "blocked_1"
    
    def test_priority_rankings(self):
        """Test getting priority rankings for multiple tasks."""
        calc = FluidDynamicsPriorityCalculator()
        
        # Create tasks with different priorities
        high_priority = Task("high", "High Priority", "production", base_priority=5.0)
        
        medium_blocked = Task("medium", "Medium with Blocked Dep", "production", base_priority=2.0)
        blocked_dep = Task("blocked", "Blocked Dependency", "production", base_priority=3.0)
        blocked_dep.mark_blocked()
        medium_blocked.upstream_dependencies.add("blocked")
        
        low_priority = Task("low", "Low Priority", "production", base_priority=1.0)
        
        calc.add_task(high_priority)
        calc.add_task(medium_blocked)
        calc.add_task(blocked_dep)
        calc.add_task(low_priority)
        
        rankings = calc.get_priority_rankings()
        
        # Should have all tasks ranked by priority
        assert len(rankings) == 4
        
        # Extract task IDs and priorities in ranking order
        ranked_items = [(ranking[0], ranking[1]) for ranking in rankings]
        
        # The blocked task itself should have highest priority (self-blocked: 3.0 + 3.0 = 6.0)
        # Medium task with blocked dependency should be second (2.0 + 3.0 = 5.0)
        # High priority task should be third (base priority 5.0)
        # Low priority task should be last (base priority 1.0)
        assert ranked_items[0][0] == "blocked"
        assert abs(ranked_items[0][1] - 6.0) < 0.01  # Allow for floating point precision
        
        # Medium and high should both be around 5.0, so check they're above low priority
        assert abs(ranked_items[1][1] - 5.0) < 0.01  # medium or high
        assert abs(ranked_items[2][1] - 5.0) < 0.01  # medium or high
        assert ranked_items[3][0] == "low"
        assert ranked_items[3][1] == 1.0
    
    def test_circular_dependency_handling(self):
        """Test that circular dependencies don't cause infinite loops."""
        calc = FluidDynamicsPriorityCalculator()
        
        # Create circular dependency: task1 -> task2 -> task1
        task1 = Task("task1", "Task 1", "production", base_priority=1.0)
        task2 = Task("task2", "Task 2", "production", base_priority=2.0)
        
        task1.upstream_dependencies.add("task2")
        task2.upstream_dependencies.add("task1")
        task2.mark_blocked()  # Block one to test the calculation
        
        calc.add_task(task1)
        calc.add_task(task2)
        
        # This should not hang or crash
        priority, details = calc.calculate_fluid_pressure("task1")
        
        # Should find the blocked task despite the cycle
        assert priority >= 1.0
        assert details["blocked_count"] >= 0
    
    def test_time_based_priority_increase(self):
        """Test that longer blocked duration increases priority."""
        calc = FluidDynamicsPriorityCalculator(time_pressure_factor=0.1)
        
        # Create a blocked task with simulated blocked time
        blocked_task = Task("blocked_1", "Blocked Task", "production", base_priority=2.0)
        blocked_task.mark_blocked()
        # Simulate task blocked for 5 hours
        blocked_task.blocked_since = datetime.utcnow() - timedelta(hours=5)
        
        test_task = Task("test_1", "Test Task", "production", base_priority=1.0)
        test_task.upstream_dependencies.add("blocked_1")
        
        calc.add_task(blocked_task)
        calc.add_task(test_task)
        
        priority, details = calc.calculate_fluid_pressure("test_1")
        
        # Time multiplier should be > 1.0 due to 5 hours of blocking
        assert details["time_multiplier"] > 1.0
        assert details["max_blocked_hours"] >= 4.5  # Allow some precision loss
        
        # Priority should be higher due to time pressure
        base_priority_calc = 2.0 * 1.0 + 1.0  # If time multiplier was 1.0
        assert priority > base_priority_calc


if __name__ == "__main__":
    pytest.main([__file__])