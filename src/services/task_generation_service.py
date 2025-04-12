"""
Task generation service module for automatically creating tasks based on inventory levels.

This module provides the TaskGenerationService class which:
- Monitors inventory levels across locations
- Generates tasks based on deficits and item importance
- Calculates task priorities based on multiple factors
- Creates appropriate tasks for different types of deficits
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.database_manager import DatabaseManager
from src.models.task import Task, TaskType, TaskStatus
from src.models.inventory import Inventory
from src.models.item import Item
from src.models.location import Location
from src.services.task_service import TaskService

logger = logging.getLogger(__name__)

class TaskGenerationService:
    """Service for generating tasks based on inventory levels."""
    
    def __init__(self, database_manager: DatabaseManager, task_service: TaskService):
        """Initialize the task generation service.
        
        Args:
            database_manager: The database manager to use for database operations
            task_service: The task service to use for task operations
        """
        self.database_manager = database_manager
        self.task_service = task_service
        self.check_interval = timedelta(minutes=15)  # Check inventory every 15 minutes
        self.min_deficit_threshold = 0.2  # 20% deficit threshold for task generation
        self.critical_deficit_threshold = 0.5  # 50% deficit threshold for critical tasks
        
        # Default buffer levels for different building types
        self.building_buffer_levels = {
            "Bunker": 0.3,  # 30% buffer for bunkers
            "Safehouse": 0.4,  # 40% buffer for safehouses
            "Garrison House": 0.5,  # 50% buffer for garrison houses
            "Town Hall": 0.6,  # 60% buffer for town halls
            "Storage Depot": 0.8,  # 80% buffer for storage depots
            "Seaport": 0.9,  # 90% buffer for seaports
            "Factory": 0.7,  # 70% buffer for factories
            "Refinery": 0.7,  # 70% buffer for refineries
            "Mass Production Factory": 0.8,  # 80% buffer for MPFs
            "Small Assembly Plant": 0.6,  # 60% buffer for SAPs
            "Large Assembly Plant": 0.7,  # 70% buffer for LAPs
            "Advanced Assembly Plant": 0.8,  # 80% buffer for AAPs
            "Default": 0.5  # 50% default buffer
        }
    
    async def start_monitoring(self):
        """Start monitoring inventory levels and generating tasks."""
        logger.info("Starting inventory monitoring for task generation")
        while True:
            try:
                await self.check_inventory_and_generate_tasks()
            except Exception as e:
                logger.error(f"Error in inventory monitoring: {e}")
            
            await asyncio.sleep(self.check_interval.total_seconds())
    
    async def check_inventory_and_generate_tasks(self):
        """Check inventory levels and generate tasks as needed."""
        logger.info("Checking inventory levels for task generation")
        
        # Get all locations with their current inventory
        async with self.database_manager.get_session() as session:
            # Get all locations
            locations_result = await session.execute(select(Location))
            locations = locations_result.scalars().all()
            
            for location in locations:
                # Get inventory for this location
                inventory_result = await session.execute(
                    select(Inventory)
                    .where(Inventory.location_id == location.id)
                )
                inventory_items = inventory_result.scalars().all()
                
                # Get all items to check against
                items_result = await session.execute(select(Item))
                all_items = items_result.scalars().all()
                
                # Create a map of item_id to inventory quantity
                inventory_map = {item.item_id: item.quantity for item in inventory_items}
                
                # Check each item for deficits
                for item in all_items:
                    current_quantity = inventory_map.get(item.id, 0)
                    target_quantity = item.target_quantity
                    
                    if target_quantity <= 0:
                        continue  # Skip items with no target quantity
                    
                    # Calculate deficit percentage
                    deficit_percentage = 1 - (current_quantity / target_quantity) if target_quantity > 0 else 0
                    
                    # Skip if deficit is below threshold
                    if deficit_percentage < self.min_deficit_threshold:
                        continue
                    
                    # Determine task priority based on item importance and deficit
                    priority = self._calculate_task_priority(item, deficit_percentage)
                    
                    # Skip if priority is too low (optional tasks)
                    if priority < 3:
                        continue
                    
                    # Determine task type based on item and location
                    task_type = self._determine_task_type(item, location)
                    
                    # Find source location for the item
                    source_location = await self._find_source_location(session, item, location)
                    
                    if not source_location:
                        logger.warning(f"No source location found for item {item.name} at {location.name}")
                        continue
                    
                    # Create task description
                    description = self._create_task_description(item, location, source_location, current_quantity, target_quantity)
                    
                    # Create the task
                    await self.task_service.create_task(
                        item_name=item.name,
                        item_quantity=target_quantity - current_quantity,
                        item_category=item.category,
                        source_location=source_location.name,
                        source_building=source_location.building_type,
                        destination_location=location.name,
                        destination_building=location.building_type,
                        task_type=task_type,
                        description=description,
                        notes=f"Auto-generated task based on inventory deficit ({int(deficit_percentage * 100)}% deficit)",
                        estimated_time=self._estimate_task_time(item, target_quantity - current_quantity),
                        priority=priority
                    )
    
    def _calculate_task_priority(self, item: Item, deficit_percentage: float) -> int:
        """Calculate task priority based on item importance and deficit.
        
        Args:
            item: The item to calculate priority for
            deficit_percentage: The percentage deficit (0-1)
            
        Returns:
            Priority value (1-10)
        """
        # Base priority on item importance (1-5)
        base_priority = item.importance
        
        # Adjust based on deficit percentage
        deficit_factor = 1.0
        if deficit_percentage >= self.critical_deficit_threshold:
            deficit_factor = 2.0  # Double priority for critical deficits
        elif deficit_percentage >= 0.3:
            deficit_factor = 1.5  # 50% boost for significant deficits
        
        # Calculate final priority (1-10)
        priority = int(base_priority * deficit_factor)
        
        # Ensure priority is within valid range
        return max(1, min(10, priority))
    
    def _determine_task_type(self, item: Item, location: Location) -> TaskType:
        """Determine the task type based on item and location.
        
        Args:
            item: The item
            location: The destination location
            
        Returns:
            The task type
        """
        # If the location is a production facility and the item can be produced there
        if location.building_type in ["Factory", "Refinery", "Mass Production Factory", 
                                     "Small Assembly Plant", "Large Assembly Plant", "Advanced Assembly Plant"]:
            if item.can_be_produced:
                return TaskType.PRODUCTION
        
        # Default to transport
        return TaskType.TRANSPORT
    
    async def _find_source_location(self, session: AsyncSession, item: Item, destination: Location) -> Optional[Location]:
        """Find a suitable source location for an item.
        
        Args:
            session: The database session
            item: The item to find a source for
            destination: The destination location
            
        Returns:
            A suitable source location, or None if none found
        """
        # First, try to find locations with surplus of this item
        inventory_result = await session.execute(
            select(Inventory, Location)
            .join(Location, Inventory.location_id == Location.id)
            .where(
                and_(
                    Inventory.item_id == item.id,
                    Inventory.quantity > Inventory.target_quantity * 1.1,  # 10% surplus
                    Location.id != destination.id  # Not the destination
                )
            )
            .order_by(desc(Inventory.quantity - Inventory.target_quantity))
        )
        
        source_candidates = inventory_result.all()
        
        if source_candidates:
            # Return the location with the highest surplus
            return source_candidates[0][1]
        
        # If no surplus found, look for locations that can produce this item
        if item.can_be_produced:
            production_locations_result = await session.execute(
                select(Location)
                .where(
                    and_(
                        Location.building_type.in_([
                            "Factory", "Refinery", "Mass Production Factory",
                            "Small Assembly Plant", "Large Assembly Plant", "Advanced Assembly Plant"
                        ]),
                        Location.id != destination.id
                    )
                )
            )
            
            production_locations = production_locations_result.scalars().all()
            
            if production_locations:
                # Return the closest production facility
                # For simplicity, just return the first one
                return production_locations[0]
        
        # If still no source found, look for any location with this item
        any_inventory_result = await session.execute(
            select(Inventory, Location)
            .join(Location, Inventory.location_id == Location.id)
            .where(
                and_(
                    Inventory.item_id == item.id,
                    Inventory.quantity > 0,
                    Location.id != destination.id
                )
            )
            .order_by(desc(Inventory.quantity))
        )
        
        any_candidates = any_inventory_result.all()
        
        if any_candidates:
            return any_candidates[0][1]
        
        # No source found
        return None
    
    def _create_task_description(self, item: Item, destination: Location, source: Location, 
                                 current_quantity: int, target_quantity: int) -> str:
        """Create a task description.
        
        Args:
            item: The item
            destination: The destination location
            source: The source location
            current_quantity: Current quantity at destination
            target_quantity: Target quantity at destination
            
        Returns:
            A task description
        """
        quantity_needed = target_quantity - current_quantity
        
        if source.building_type in ["Factory", "Refinery", "Mass Production Factory", 
                                   "Small Assembly Plant", "Large Assembly Plant", "Advanced Assembly Plant"]:
            return f"Produce {quantity_needed} {item.name} at {source.name} and transport to {destination.name}"
        else:
            return f"Transport {quantity_needed} {item.name} from {source.name} to {destination.name}"
    
    def _estimate_task_time(self, item: Item, quantity: int) -> int:
        """Estimate the time needed to complete a task in minutes.
        
        Args:
            item: The item
            quantity: The quantity needed
            
        Returns:
            Estimated time in minutes
        """
        # Base time per item (in minutes)
        base_time_per_item = 1
        
        # Adjust based on item category
        category_multipliers = {
            "Ammunition": 1.2,
            "Medical": 1.5,
            "Supplies": 1.0,
            "Resources": 1.3,
            "Vehicles": 2.0,
            "Weapons": 1.8,
            "Default": 1.0
        }
        
        multiplier = category_multipliers.get(item.category, category_multipliers["Default"])
        
        # Calculate base time
        base_time = quantity * base_time_per_item * multiplier
        
        # Add overhead time
        overhead_time = 15  # 15 minutes overhead
        
        # Calculate total time
        total_time = base_time + overhead_time
        
        # Ensure minimum time of 30 minutes
        return max(30, int(total_time))
    
    async def get_inventory_status(self, location_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get the current inventory status for all locations or a specific location.
        
        Args:
            location_id: Optional location ID to filter by
            
        Returns:
            List of inventory status dictionaries
        """
        async with self.database_manager.get_session() as session:
            query = select(Inventory, Item, Location)
            
            if location_id:
                query = query.where(Inventory.location_id == location_id)
            
            query = query.join(Item, Inventory.item_id == Item.id)
            query = query.join(Location, Inventory.location_id == Location.id)
            
            result = await session.execute(query)
            rows = result.all()
            
            status_list = []
            for inventory, item, location in rows:
                deficit = 1 - (inventory.quantity / item.target_quantity) if item.target_quantity > 0 else 0
                
                status_list.append({
                    "location_id": location.id,
                    "location_name": location.name,
                    "building_type": location.building_type,
                    "item_id": item.id,
                    "item_name": item.name,
                    "item_category": item.category,
                    "current_quantity": inventory.quantity,
                    "target_quantity": item.target_quantity,
                    "deficit_percentage": deficit,
                    "status": self._get_inventory_status(deficit)
                })
            
            return status_list
    
    def _get_inventory_status(self, deficit_percentage: float) -> str:
        """Get the status string for an inventory level.
        
        Args:
            deficit_percentage: The percentage deficit (0-1)
            
        Returns:
            Status string
        """
        if deficit_percentage >= self.critical_deficit_threshold:
            return "Critical"
        elif deficit_percentage >= 0.3:
            return "Low"
        elif deficit_percentage >= self.min_deficit_threshold:
            return "Medium"
        else:
            return "Good" 