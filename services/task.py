"""
Task system entry point.

This module provides access to the task management and priority calculation system.
For the full implementation, see services.tasks package.
"""

# Re-export the main components for backward compatibility
from .tasks import Task, TaskStatus, FluidDynamicsPriorityCalculator, GraphTaskIntegrator

__all__ = ['Task', 'TaskStatus', 'FluidDynamicsPriorityCalculator', 'GraphTaskIntegrator']
