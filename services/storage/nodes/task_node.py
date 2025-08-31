"""
PersistentTaskNode - Task nodes with dependency management.

Specialized persistent node for task management with dependency tracking,
progress monitoring, order associations, and workflow coordination.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from persistent.list import PersistentList
from persistent.mapping import PersistentMapping

from .base_node import PersistentBaseNode

logger = logging.getLogger(__name__)


class PersistentTaskNode(PersistentBaseNode):
    """
    Persistent node for task management and workflow coordination.

    Extends PersistentBaseNode with task-specific functionality including
    dependency management, progress tracking, order associations, and workflow states.
    """

    def __init__(
        self,
        node_id: Optional[str] = None,
        name: str = "",
        task_type: str = "logistics",
        **kwargs,
    ):
        """
        Initialize task node.

        Args:
            node_id: Unique identifier for the node
            name: Human-readable name for the node
            task_type: Type of task (logistics, production, transport, etc.)
            **kwargs: Additional attributes
        """
        super().__init__(node_id=node_id, name=name, node_type="task", **kwargs)

        # Task classification
        self.task_type = task_type
        self.category = kwargs.get("category", "general")
        self.subcategory = kwargs.get("subcategory", "")

        # Task status and progress
        self.task_status = kwargs.get(
            "task_status", "pending"
        )  # pending, active, completed, failed, cancelled
        self.progress_percentage = kwargs.get("progress_percentage", 0.0)
        self.estimated_duration = kwargs.get("estimated_duration", None)  # in seconds
        self.actual_duration = kwargs.get("actual_duration", None)

        # Timing and scheduling
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.scheduled_start = kwargs.get("scheduled_start", None)
        self.actual_start = kwargs.get("actual_start", None)
        self.scheduled_completion = kwargs.get("scheduled_completion", None)
        self.actual_completion = kwargs.get("actual_completion", None)
        self.deadline = kwargs.get("deadline", None)

        # Dependencies and relationships
        self.dependencies = PersistentList()  # Tasks that must complete before this one
        self.dependents = PersistentList()  # Tasks that depend on this one
        self.blocking_tasks = PersistentList()  # Tasks this one is blocking
        self.related_tasks = PersistentList()  # Related but not dependent tasks

        # Order and workflow associations
        self.order_id = kwargs.get("order_id", None)
        self.workflow_id = kwargs.get("workflow_id", None)
        self.parent_task_id = kwargs.get("parent_task_id", None)
        self.subtasks = PersistentList()

        # Priority and resource management
        self.priority_level = kwargs.get(
            "priority_level", "normal"
        )  # low, normal, high, critical
        self.priority_score = kwargs.get(
            "priority_score", 50.0
        )  # 0-100 numeric priority
        self.resource_requirements = PersistentMapping(
            kwargs.get("resource_requirements", {})
        )
        self.allocated_resources = PersistentMapping()

        # Assignment and responsibility
        self.assigned_to = kwargs.get("assigned_to", None)  # User ID or bot ID
        self.assigned_team = kwargs.get("assigned_team", None)
        self.creator_id = kwargs.get("creator_id", None)
        self.reviewer_id = kwargs.get("reviewer_id", None)

        # Task details and configuration
        self.description = kwargs.get("description", "")
        self.instructions = PersistentList(kwargs.get("instructions", []))
        self.parameters = PersistentMapping(kwargs.get("parameters", {}))
        self.context = PersistentMapping(kwargs.get("context", {}))

        # Execution and results
        self.execution_logs = PersistentList()
        self.error_logs = PersistentList()
        self.results = PersistentMapping()
        self.output_data = PersistentMapping()

        # Quality and validation
        self.validation_rules = PersistentList()
        self.validation_results = PersistentMapping()
        self.quality_score = kwargs.get("quality_score", None)

        # Retry and error handling
        self.max_retries = kwargs.get("max_retries", 3)
        self.retry_count = kwargs.get("retry_count", 0)
        self.retry_delay = kwargs.get("retry_delay", 60)  # seconds
        self.auto_retry = kwargs.get("auto_retry", True)

        logger.debug(f"Created task node: {self.node_id} ({task_type}) - {name}")

    def add_dependency(self, task_id: str, dependency_type: str = "blocks") -> bool:
        """
        Add a dependency to this task.

        Args:
            task_id: ID of the task this one depends on
            dependency_type: Type of dependency (blocks, enables, requires)

        Returns:
            True if dependency was added
        """
        dependency = PersistentMapping(
            {
                "task_id": task_id,
                "dependency_type": dependency_type,
                "added_at": datetime.utcnow(),
            }
        )

        # Check for circular dependencies (simplified check)
        if task_id == self.node_id:
            logger.warning(f"Cannot add self as dependency for task {self.node_id}")
            return False

        # Check if dependency already exists
        for existing in self.dependencies:
            if existing["task_id"] == task_id:
                logger.warning(
                    f"Dependency {task_id} already exists for task {self.node_id}"
                )
                return False

        self.dependencies.append(dependency)
        self.update_modified_time()
        logger.debug(f"Added dependency {task_id} to task {self.node_id}")
        return True

    def remove_dependency(self, task_id: str) -> bool:
        """
        Remove a dependency from this task.

        Args:
            task_id: ID of the task dependency to remove

        Returns:
            True if dependency was removed
        """
        for i, dependency in enumerate(self.dependencies):
            if dependency["task_id"] == task_id:
                del self.dependencies[i]
                self.update_modified_time()
                logger.debug(f"Removed dependency {task_id} from task {self.node_id}")
                return True
        return False

    def add_subtask(self, subtask_id: str) -> bool:
        """
        Add a subtask to this task.

        Args:
            subtask_id: ID of the subtask

        Returns:
            True if subtask was added
        """
        if subtask_id not in self.subtasks:
            self.subtasks.append(subtask_id)
            self.update_modified_time()
            logger.debug(f"Added subtask {subtask_id} to task {self.node_id}")
            return True
        return False

    def remove_subtask(self, subtask_id: str) -> bool:
        """
        Remove a subtask from this task.

        Args:
            subtask_id: ID of the subtask to remove

        Returns:
            True if subtask was removed
        """
        if subtask_id in self.subtasks:
            self.subtasks.remove(subtask_id)
            self.update_modified_time()
            logger.debug(f"Removed subtask {subtask_id} from task {self.node_id}")
            return True
        return False

    def start_task(self, assigned_to: Optional[str] = None) -> bool:
        """
        Start the task execution.

        Args:
            assigned_to: Optional user/bot ID to assign task to

        Returns:
            True if task was started successfully
        """
        if self.task_status != "pending":
            logger.warning(
                f"Cannot start task {self.node_id} with status {self.task_status}"
            )
            return False

        # Check dependencies
        if not self.are_dependencies_satisfied():
            logger.warning(f"Dependencies not satisfied for task {self.node_id}")
            return False

        self.task_status = "active"
        self.actual_start = datetime.utcnow()
        self.progress_percentage = 0.0

        if assigned_to:
            self.assigned_to = assigned_to

        self.log_execution("Task started")
        self.update_modified_time()

        logger.info(f"Started task {self.node_id}: {self.name}")
        return True

    def update_progress(self, percentage: float, message: str = "") -> bool:
        """
        Update task progress.

        Args:
            percentage: Progress percentage (0-100)
            message: Optional progress message

        Returns:
            True if progress was updated
        """
        if self.task_status not in ["active", "pending"]:
            logger.warning(
                f"Cannot update progress for task {self.node_id} with status {self.task_status}"
            )
            return False

        percentage = max(0.0, min(100.0, percentage))
        self.progress_percentage = percentage

        if message:
            self.log_execution(f"Progress: {percentage}% - {message}")

        # Auto-complete if 100%
        if percentage >= 100.0 and self.task_status == "active":
            self.complete_task(success=True)

        self.update_modified_time()
        return True

    def complete_task(
        self, success: bool = True, results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Complete the task.

        Args:
            success: Whether the task completed successfully
            results: Optional results data

        Returns:
            True if task was completed
        """
        if self.task_status not in ["active", "pending"]:
            logger.warning(
                f"Cannot complete task {self.node_id} with status {self.task_status}"
            )
            return False

        self.actual_completion = datetime.utcnow()

        if success:
            self.task_status = "completed"
            self.progress_percentage = 100.0
            self.log_execution("Task completed successfully")
        else:
            self.task_status = "failed"
            self.log_execution("Task failed")

        # Calculate actual duration
        if self.actual_start:
            self.actual_duration = (
                self.actual_completion - self.actual_start
            ).total_seconds()

        # Store results
        if results:
            self.results.update(results)

        self.update_modified_time()
        logger.info(f"Completed task {self.node_id}: {self.name} (success: {success})")
        return True

    def cancel_task(self, reason: str = "") -> bool:
        """
        Cancel the task.

        Args:
            reason: Reason for cancellation

        Returns:
            True if task was cancelled
        """
        if self.task_status in ["completed", "cancelled"]:
            logger.warning(
                f"Cannot cancel task {self.node_id} with status {self.task_status}"
            )
            return False

        self.task_status = "cancelled"
        self.actual_completion = datetime.utcnow()

        if reason:
            self.log_execution(f"Task cancelled: {reason}")
        else:
            self.log_execution("Task cancelled")

        self.update_modified_time()
        logger.info(f"Cancelled task {self.node_id}: {self.name}")
        return True

    def retry_task(self) -> bool:
        """
        Retry a failed task.

        Returns:
            True if retry was initiated
        """
        if self.task_status != "failed":
            logger.warning(
                f"Cannot retry task {self.node_id} with status {self.task_status}"
            )
            return False

        if self.retry_count >= self.max_retries:
            logger.warning(
                f"Max retries ({self.max_retries}) exceeded for task {self.node_id}"
            )
            return False

        self.retry_count += 1
        self.task_status = "pending"
        self.progress_percentage = 0.0
        self.actual_start = None
        self.actual_completion = None

        self.log_execution(f"Task retry #{self.retry_count}")
        self.update_modified_time()

        logger.info(
            f"Retrying task {self.node_id}: {self.name} (attempt {self.retry_count})"
        )
        return True

    def are_dependencies_satisfied(self) -> bool:
        """
        Check if all dependencies are satisfied.

        Returns:
            True if all dependencies are satisfied
        """
        # This is a simplified check - in a real implementation,
        # you would check the actual status of dependent tasks
        for dependency in self.dependencies:
            dependency_type = dependency.get("dependency_type", "blocks")
            if dependency_type == "blocks":
                # Would need to check if the dependency task is completed
                # For now, assume satisfied
                pass

        return True

    def log_execution(self, message: str, level: str = "info"):
        """
        Log an execution message.

        Args:
            message: Log message
            level: Log level (info, warning, error)
        """
        log_entry = PersistentMapping(
            {"timestamp": datetime.utcnow(), "level": level, "message": message}
        )

        if level == "error":
            self.error_logs.append(log_entry)
        else:
            self.execution_logs.append(log_entry)

        self.update_modified_time()

    def set_priority(self, priority_level: str, priority_score: Optional[float] = None):
        """
        Set task priority.

        Args:
            priority_level: Priority level (low, normal, high, critical)
            priority_score: Optional numeric priority score (0-100)
        """
        self.priority_level = priority_level

        if priority_score is not None:
            self.priority_score = max(0.0, min(100.0, priority_score))
        else:
            # Set default scores based on level
            score_mapping = {
                "low": 25.0,
                "normal": 50.0,
                "high": 75.0,
                "critical": 95.0,
            }
            self.priority_score = score_mapping.get(priority_level, 50.0)

        self.update_modified_time()

    def allocate_resource(self, resource_type: str, amount: float, source: str = ""):
        """
        Allocate a resource to this task.

        Args:
            resource_type: Type of resource
            amount: Amount to allocate
            source: Source of the resource
        """
        if resource_type not in self.allocated_resources:
            self.allocated_resources[resource_type] = PersistentMapping()

        allocation = PersistentMapping(
            {"amount": amount, "source": source, "allocated_at": datetime.utcnow()}
        )

        self.allocated_resources[resource_type] = allocation
        self.update_modified_time()

    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get execution summary statistics.

        Returns:
            Dictionary with execution summary
        """
        now = datetime.utcnow()

        summary = {
            "task_id": self.node_id,
            "task_status": self.task_status,
            "progress_percentage": self.progress_percentage,
            "priority_level": self.priority_level,
            "priority_score": self.priority_score,
            "retry_count": self.retry_count,
            "dependencies_count": len(self.dependencies),
            "subtasks_count": len(self.subtasks),
            "execution_logs_count": len(self.execution_logs),
            "error_logs_count": len(self.error_logs),
        }

        # Timing information
        if self.scheduled_start:
            summary["scheduled_start"] = self.scheduled_start.isoformat()
        if self.actual_start:
            summary["actual_start"] = self.actual_start.isoformat()
            if self.task_status == "active":
                summary["elapsed_time"] = (now - self.actual_start).total_seconds()
        if self.actual_completion:
            summary["actual_completion"] = self.actual_completion.isoformat()
        if self.actual_duration:
            summary["actual_duration"] = self.actual_duration

        return summary

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        base_dict = super().to_dict()

        task_dict = {
            "task_type": self.task_type,
            "category": self.category,
            "subcategory": self.subcategory,
            "task_status": self.task_status,
            "progress_percentage": self.progress_percentage,
            "priority_level": self.priority_level,
            "priority_score": self.priority_score,
            "order_id": self.order_id,
            "workflow_id": self.workflow_id,
            "parent_task_id": self.parent_task_id,
            "assigned_to": self.assigned_to,
            "assigned_team": self.assigned_team,
            "description": self.description,
            "dependencies": [dict(d) for d in self.dependencies],
            "subtasks": list(self.subtasks),
            "resource_requirements": dict(self.resource_requirements),
            "allocated_resources": {
                k: dict(v) for k, v in self.allocated_resources.items()
            },
            "parameters": dict(self.parameters),
            "results": dict(self.results),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "execution_summary": self.get_execution_summary(),
        }

        base_dict.update(task_dict)
        return base_dict
