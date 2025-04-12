"""
Task model module for defining the structure of tasks.

This module provides:
- TaskStatus enum for task status values
- TaskPriority enum for task priority values
- TaskType enum for task type values
- Task model class for task data
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class TaskStatus(enum.Enum):
    """Enum for task status values."""
    AVAILABLE = "available"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    STALE = "stale"
    RELEASED = "released"

class TaskPriority(enum.Enum):
    """Enum for task priority values."""
    CRITICAL = 10
    HIGH = 7
    MEDIUM = 5
    LOW = 3
    OPTIONAL = 1

class TaskType(enum.Enum):
    """Enum for task type values."""
    TRANSPORT = "transport"
    PRODUCTION = "production"
    REDISTRIBUTION = "redistribution"

class Task(Base):
    """Model class for task data."""
    
    __tablename__ = "tasks"
    
    # Primary key
    id = Column(String, primary_key=True)
    
    # Status and priority
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.AVAILABLE)
    priority = Column(Integer, nullable=False, default=5)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, nullable=False)
    claimed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    auto_release = Column(DateTime, nullable=True)
    
    # User assignment
    claimed_by = Column(String, nullable=True)
    
    # Item details
    item_name = Column(String, nullable=False)
    item_quantity = Column(Integer, nullable=False)
    item_category = Column(String, nullable=False)
    
    # Location details
    source_location = Column(String, nullable=False)
    source_building = Column(String, nullable=False)
    destination_location = Column(String, nullable=False)
    destination_building = Column(String, nullable=False)
    
    # Task details
    task_type = Column(Enum(TaskType), nullable=False)
    description = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    estimated_time = Column(Integer, nullable=False, default=30)  # in minutes
    progress = Column(Integer, nullable=True, default=0)  # 0-100
    
    def __repr__(self):
        """Return a string representation of the task."""
        return (
            f"<Task(id='{self.id}', "
            f"status='{self.status.value}', "
            f"priority={self.priority}, "
            f"item='{self.item_name}', "
            f"quantity={self.item_quantity}, "
            f"type='{self.task_type.value}')>"
        )
    
    def to_dict(self) -> dict:
        """Convert the task to a dictionary."""
        return {
            "id": self.id,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "claimed_at": self.claimed_at.isoformat() if self.claimed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "auto_release": self.auto_release.isoformat() if self.auto_release else None,
            "claimed_by": self.claimed_by,
            "item_name": self.item_name,
            "item_quantity": self.item_quantity,
            "item_category": self.item_category,
            "source_location": self.source_location,
            "source_building": self.source_building,
            "destination_location": self.destination_location,
            "destination_building": self.destination_building,
            "task_type": self.task_type.value,
            "description": self.description,
            "notes": self.notes,
            "estimated_time": self.estimated_time,
            "progress": self.progress
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create a task from a dictionary.
        
        Args:
            data: Dictionary containing task data
            
        Returns:
            A new Task instance
        """
        # Convert string status to enum
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TaskStatus(data["status"])
        
        # Convert string task type to enum
        if "task_type" in data and isinstance(data["task_type"], str):
            data["task_type"] = TaskType(data["task_type"])
        
        # Convert ISO format strings to datetime objects
        for field in ["created_at", "last_updated", "claimed_at", "completed_at", "auto_release"]:
            if field in data and data[field] and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])
        
        return cls(**data) 