"""Task representation for the priority system."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class TaskStatus(Enum):
    """Status of a task in the system."""

    PENDING = "pending"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    QUEUED = "queued"


@dataclass
class Task:
    """Represents a task in the logistics system.
    Tasks can be production, transport, or supply tasks that may be blocked by upstream dependencies.
    """

    name: str
    task_type: str  # e.g., "production", "transport", "supply"
    task_id: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    base_priority: float = 1.0  # Base priority weight from priority table
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.UTC))
    blocked_since: datetime | None = None
    upstream_dependencies: set[str] = field(default_factory=set)
    downstream_dependents: set[str] = field(default_factory=set)
    metadata: dict[str, any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Assign a unique ID if not provided."""
        if self.task_id is None:
            self.task_id = self._generate_unique_id()

    @staticmethod
    def _generate_unique_id() -> str:
        """Generate a unique task ID."""
        import uuid
        return str(uuid.uuid4())

    def mark_blocked(self) -> None:
        """Mark this task as blocked and record the time."""
        if self.status != TaskStatus.BLOCKED:
            self.status = TaskStatus.BLOCKED
            self.blocked_since = datetime.now(timezone.UTC)
    
    def mark_unblocked(self) -> None:
        """Mark this task as no longer blocked."""
        if self.status == TaskStatus.BLOCKED:
            self.status = TaskStatus.PENDING
            self.blocked_since = None
    
    def get_blocked_duration_hours(self) -> float:
        """Get how long this task has been blocked in hours."""
        if self.blocked_since is None:
            return 0.0
        return (datetime.now(timezone.UTC) - self.blocked_since).total_seconds() / 3600.0
    
    def __repr__(self) -> str:
        """Return string representation of the task."""
        return "Task({}, {}, {})".format(self.task_id, self.name, self.status.value)