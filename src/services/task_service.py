"""
Task service module for handling task-related business logic.

This module provides the TaskService class which manages:
- Task creation and retrieval
- Task status updates
- Task claiming and releasing
- Auto-release functionality
- Task filtering
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from src.models.task import Task, TaskStatus, TaskPriority, TaskType
from src.database.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class TaskService:
    """Service for handling task-related business logic."""
    
    def __init__(self, database_manager: DatabaseManager):
        """Initialize the task service.
        
        Args:
            database_manager: The database manager to use for database operations
        """
        self.database_manager = database_manager
        self.auto_release_interval = timedelta(hours=2)
    
    async def create_task(
        self,
        item_name: str,
        item_quantity: int,
        item_category: str,
        source_location: str,
        source_building: str,
        destination_location: str,
        destination_building: str,
        task_type: TaskType,
        description: str,
        notes: Optional[str] = None,
        estimated_time: int = 30,
        priority: int = 5
    ) -> Task:
        """Create a new task.
        
        Args:
            item_name: The name of the item
            item_quantity: The quantity of the item
            item_category: The category of the item
            source_location: The source location
            source_building: The source building
            destination_location: The destination location
            destination_building: The destination building
            task_type: The type of task
            description: The task description
            notes: Additional notes
            estimated_time: Estimated time to complete in minutes
            priority: Task priority (1-10)
            
        Returns:
            The created task
        """
        task_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        task = Task(
            id=task_id,
            status=TaskStatus.AVAILABLE,
            priority=priority,
            created_at=now,
            last_updated=now,
            item_name=item_name,
            item_quantity=item_quantity,
            item_category=item_category,
            source_location=source_location,
            source_building=source_building,
            destination_location=destination_location,
            destination_building=destination_building,
            task_type=task_type,
            description=description,
            notes=notes,
            estimated_time=estimated_time
        )
        
        async with self.database_manager.get_session() as session:
            session.add(task)
            await session.commit()
            await session.refresh(task)
        
        logger.info(f"Created task {task_id}: {description}")
        return task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task if found, None otherwise
        """
        async with self.database_manager.get_session() as session:
            result = await session.execute(select(Task).where(Task.id == task_id))
            return result.scalar_one_or_none()
    
    async def get_tasks(
        self,
        priority: Optional[str] = None,
        location: Optional[str] = None,
        item: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Task]:
        """Get tasks with optional filtering.
        
        Args:
            priority: Filter by priority level
            location: Filter by location
            item: Filter by item type
            status: Filter by status
            
        Returns:
            List of tasks matching the criteria
        """
        async with self.database_manager.get_session() as session:
            query = select(Task)
            
            # Apply filters
            if priority:
                priority_map = {
                    "critical": 8,
                    "high": 5,
                    "medium": 3,
                    "low": 1
                }
                if priority.lower() in priority_map:
                    query = query.where(Task.priority >= priority_map[priority.lower()])
            
            if location:
                query = query.where(
                    or_(
                        Task.source_location.ilike(f"%{location}%"),
                        Task.destination_location.ilike(f"%{location}%")
                    )
                )
            
            if item:
                query = query.where(
                    or_(
                        Task.item_name.ilike(f"%{item}%"),
                        Task.item_category.ilike(f"%{item}%")
                    )
                )
            
            if status:
                try:
                    task_status = TaskStatus(status.lower())
                    query = query.where(Task.status == task_status)
                except ValueError:
                    logger.warning(f"Invalid status filter: {status}")
            
            # Order by priority (descending) and creation time (ascending)
            query = query.order_by(Task.priority.desc(), Task.created_at.asc())
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def claim_task(self, task_id: str, user_id: str) -> Optional[Task]:
        """Claim a task for a user.
        
        Args:
            task_id: The task ID
            user_id: The user ID
            
        Returns:
            The updated task if successful, None otherwise
        """
        async with self.database_manager.get_session() as session:
            task = await self.get_task(task_id)
            if not task or task.status != TaskStatus.AVAILABLE:
                return None
            
            now = datetime.utcnow()
            task.status = TaskStatus.CLAIMED
            task.claimed_by = user_id
            task.claimed_at = now
            task.auto_release = now + self.auto_release_interval
            task.last_updated = now
            
            await session.commit()
            await session.refresh(task)
            
            logger.info(f"Task {task_id} claimed by user {user_id}")
            return task
    
    async def update_task_progress(self, task_id: str, user_id: str, progress: int, notes: Optional[str] = None) -> Optional[Task]:
        """Update the progress of a task.
        
        Args:
            task_id: The task ID
            user_id: The user ID
            progress: Progress percentage (0-100)
            notes: Additional notes
            
        Returns:
            The updated task if successful, None otherwise
        """
        async with self.database_manager.get_session() as session:
            task = await self.get_task(task_id)
            if not task or task.claimed_by != user_id or task.status not in [TaskStatus.CLAIMED, TaskStatus.IN_PROGRESS]:
                return None
            
            now = datetime.utcnow()
            task.status = TaskStatus.IN_PROGRESS
            task.progress = progress
            task.notes = notes or task.notes
            task.last_updated = now
            task.auto_release = now + self.auto_release_interval
            
            await session.commit()
            await session.refresh(task)
            
            logger.info(f"Task {task_id} progress updated to {progress}% by user {user_id}")
            return task
    
    async def complete_task(self, task_id: str, user_id: str) -> Optional[Task]:
        """Mark a task as completed.
        
        Args:
            task_id: The task ID
            user_id: The user ID
            
        Returns:
            The updated task if successful, None otherwise
        """
        async with self.database_manager.get_session() as session:
            task = await self.get_task(task_id)
            if not task or task.claimed_by != user_id or task.status not in [TaskStatus.CLAIMED, TaskStatus.IN_PROGRESS]:
                return None
            
            now = datetime.utcnow()
            task.status = TaskStatus.COMPLETED
            task.progress = 100
            task.completed_at = now
            task.last_updated = now
            
            await session.commit()
            await session.refresh(task)
            
            logger.info(f"Task {task_id} completed by user {user_id}")
            return task
    
    async def release_task(self, task_id: str, user_id: str) -> Optional[Task]:
        """Release a claimed task back to the pool.
        
        Args:
            task_id: The task ID
            user_id: The user ID
            
        Returns:
            The updated task if successful, None otherwise
        """
        async with self.database_manager.get_session() as session:
            task = await self.get_task(task_id)
            if not task or task.claimed_by != user_id or task.status not in [TaskStatus.CLAIMED, TaskStatus.IN_PROGRESS]:
                return None
            
            now = datetime.utcnow()
            task.status = TaskStatus.AVAILABLE
            task.claimed_by = None
            task.claimed_at = None
            task.auto_release = None
            task.last_updated = now
            
            await session.commit()
            await session.refresh(task)
            
            logger.info(f"Task {task_id} released by user {user_id}")
            return task
    
    async def check_auto_release(self) -> List[Task]:
        """Check for tasks that need to be auto-released.
        
        Returns:
            List of tasks that were auto-released
        """
        now = datetime.utcnow()
        auto_released_tasks = []
        
        async with self.database_manager.get_session() as session:
            # Find tasks that are claimed or in progress and past their auto-release time
            query = select(Task).where(
                and_(
                    Task.status.in_([TaskStatus.CLAIMED, TaskStatus.IN_PROGRESS]),
                    Task.auto_release <= now
                )
            )
            
            result = await session.execute(query)
            tasks_to_release = result.scalars().all()
            
            for task in tasks_to_release:
                task.status = TaskStatus.AVAILABLE
                task.claimed_by = None
                task.claimed_at = None
                task.auto_release = None
                task.last_updated = now
                auto_released_tasks.append(task)
            
            if auto_released_tasks:
                await session.commit()
                for task in auto_released_tasks:
                    logger.info(f"Task {task.id} auto-released due to inactivity")
        
        return auto_released_tasks 