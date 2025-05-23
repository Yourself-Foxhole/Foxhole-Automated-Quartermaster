"""
Task generation service module for handling task generation logic.

This module provides the TaskGenerationService class which manages:
- Task generation based on inventory levels
- Priority calculation
- Task type determination
- Source location finding
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.database_manager import DatabaseManager
from src.models.task import Task, TaskType, TaskStatus, TaskPriority
from src.models.inventory import Inventory
from src.models.item import Item
from src.models.location import Location
from src.config.priority_config import (
    get_location_priority,
    get_item_priority,
    get_deficit_multiplier,
    get_time_multiplier,
    round_to_capacity,
    get_truck_capacity,
    get_available_truck_types,
    PRIORITY_MULTIPLIERS
)
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
        self.min_deficit_threshold = 0.9  # 90% deficit minimum to generate task
        self.critical_deficit_threshold = 0.5  # 50% deficit threshold for critical tasks
        self.default_truck_type = "standard"  # Default truck type for FTL calculations
        
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
            "Default": 0.5  # 50% default buffer
        }
    
    def set_default_truck_type(self, truck_type: str):
        """Set the default truck type for FTL calculations.
        
        Args:
            truck_type: The truck type to use as default
        """
        if truck_type.lower() in get_available_truck_types():
            self.default_truck_type = truck_type.lower()
        else:
            logger.warning(f"Invalid truck type: {truck_type}. Using standard truck.")
            self.default_truck_type = "standard"
    
    async def start_monitoring(self):
        """Start monitoring inventory levels and generating tasks."""
        logger.info("Starting inventory monitoring for task generation")
        while True:
            try:
                await self._check_inventory_levels()
            except Exception as e:
                logger.error(f"Error in inventory monitoring: {e}")
            
            await asyncio.sleep(self.check_interval.total_seconds())
    
    async def _check_inventory_levels(self):
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
                    
                    # Calculate task priority components
                    base_priority = get_item_priority(item.category)
                    deficit_severity_bonus = int(base_priority * get_deficit_multiplier(deficit_percentage))
                    location_importance_bonus = int(base_priority * PRIORITY_MULTIPLIERS["location"])
                    
                    # Round quantity to appropriate capacity
                    quantity = round_to_capacity(target_quantity - current_quantity, self.default_truck_type)
                    
                    # Determine if this is an FTL or FCL
                    truck_capacity = get_truck_capacity(self.default_truck_type)
                    is_ftl = quantity == truck_capacity  # Exact FTL capacity for current truck type
                    is_fcl = quantity == 60 and not is_ftl  # Exact FCL capacity
                    
                    # Determine task type based on item and location
                    task_type = self._determine_task_type(item, location)
                    
                    # Find source location for the item
                    source_location = await self._find_source_location(session, item, location)
                    
                    if not source_location:
                        logger.warning(f"No source location found for item {item.name} at {location.name}")
                        continue
                    
                    # Create task description
                    description = self._create_task_description(
                        item, location, source_location,
                        current_quantity, target_quantity,
                        self.default_truck_type if is_ftl else None
                    )
                    
                    # Create the task
                    await self.task_service.create_task(
                        item_name=item.name,
                        item_quantity=quantity,
                        item_category=item.category,
                        source_location=source_location.name,
                        source_building=source_location.building_type,
                        destination_location=location.name,
                        destination_building=location.building_type,
                        task_type=task_type,
                        description=description,
                        notes=f"Auto-generated task based on inventory deficit ({int(deficit_percentage * 100)}% deficit)",
                        estimated_time=self._estimate_task_time(item, quantity),
                        base_priority=base_priority,
                        deficit_severity_bonus=deficit_severity_bonus,
                        location_importance_bonus=location_importance_bonus,
                        is_ftl=is_ftl,
                        is_fcl=is_fcl
                    )
    
    def _determine_task_type(self, item: Item, location: Location) -> TaskType:
        """Determine the appropriate task type based on item and location."""
        if location.building_type in ["FACTORY", "MPF"]:
            return TaskType.QUEUE_PRODUCTION
        elif location.building_type in ["BUNKER_BASE", "FOB"]:
            return TaskType.TRANSPORT_LAST_MILE
        else:
            return TaskType.TRANSPORT
    
    async def _find_source_location(self, session: AsyncSession, item: Item, destination: Location) -> Optional[Location]:
        """Find the best source location for an item."""
        # Get all locations that can produce this item
        query = select(Location).where(
            Location.building_type.in_(["FACTORY", "MPF", "STORAGE_DEPOT", "SEAPORT"])
        )
        result = await session.execute(query)
        potential_sources = result.scalars().all()
        
        if not potential_sources:
            return None
        
        # TODO: Implement more sophisticated source selection logic
        # For now, just return the first potential source
        return potential_sources[0]
    
    def _create_task_description(
        self,
        item: Item,
        destination: Location,
        source: Location,
        current_quantity: int,
        target_quantity: int,
        truck_type: Optional[str] = None
    ) -> str:
        """Create a description for the task."""
        deficit = target_quantity - current_quantity
        description = f"Transport {deficit} {item.name} from {source.name} to {destination.name}. "
        description += f"Current stock: {current_quantity}, Target: {target_quantity}"
        
        if truck_type:
            description += f" (Requires {truck_type.title()} truck)"
        
        return description
    
    def _estimate_task_time(self, item: Item, quantity: int) -> int:
        """Estimate the time required to complete the task in minutes."""
        # Base time for any task
        base_time = 30
        
        # Add time based on quantity
        quantity_time = (quantity // 15) * 10  # 10 minutes per truck load
        
        # Add time based on item category
        category_time = {
            "CRITICAL": 0,
            "COMBAT": 5,
            "SUPPORT": 10,
            "LOGISTICS": 15,
            "OPTIONAL": 20
        }.get(item.category, 15)
        
        return base_time + quantity_time + category_time
    
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