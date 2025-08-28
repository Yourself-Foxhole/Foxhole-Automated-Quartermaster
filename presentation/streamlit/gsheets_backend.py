"""Google Sheets backend for Foxhole logistics data.

This module provides a data backend layer that uses Google Sheets for persistent storage
of inventory, tasks, analytics, and location data. It integrates with the existing data
models and provides CRUD operations for the Streamlit app.
"""

import pandas as pd
import streamlit as st
from typing import Dict, List, Optional, Any, Union
from dataclasses import asdict
import json
from datetime import datetime, timedelta
import logging

from streamlit_gsheets import GSheetsConnection

from data_models import (
    Item, Location, InventoryState, ItemType, FacilityType,
    FOXHOLE_ITEMS, FOXHOLE_REGIONS, SAMPLE_LOCATIONS
)

# Import existing task system if available
try:
    from services.tasks.task import Task, TaskStatus
except ImportError:
    # Fallback for prototype
    from enum import Enum
    from dataclasses import dataclass, field
    
    class TaskStatus(Enum):
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        CANCELLED = "cancelled"
    
    @dataclass
    class Task:
        task_id: str
        name: str
        task_type: str = "transportation"
        priority: str = "medium"
        status: TaskStatus = TaskStatus.PENDING
        created_at: datetime = field(default_factory=datetime.now)
        updated_at: datetime = field(default_factory=datetime.now)
        assigned_to: Optional[str] = None
        description: str = ""


class GSheetsDataBackend:
    """Google Sheets data backend for Foxhole logistics."""
    
    def __init__(self):
        """Initialize the Google Sheets connection."""
        self.logger = logging.getLogger(__name__)
        self._connection = None
        self._connection_status = "disconnected"
        self._last_error = None
        
    @property
    def connection(self) -> Optional[GSheetsConnection]:
        """Get or create Google Sheets connection."""
        if self._connection is None:
            try:
                self._connection = st.connection("gsheets", type=GSheetsConnection)
                self._connection_status = "connected"
                self._last_error = None
                self.logger.info("Connected to Google Sheets")
            except Exception as e:
                self._connection_status = "error"
                self._last_error = str(e)
                self.logger.error(f"Failed to connect to Google Sheets: {e}")
        return self._connection
    
    @property
    def connection_status(self) -> str:
        """Get connection status."""
        return self._connection_status
    
    @property
    def last_error(self) -> Optional[str]:
        """Get last error message."""
        return self._last_error
    
    def test_connection(self) -> bool:
        """Test the connection to Google Sheets."""
        try:
            if self.connection is None:
                return False
            # Try to read a small test to verify connection
            self.connection.read(worksheet="test", ttl=0)
            return True
        except Exception as e:
            self.logger.warning(f"Connection test failed: {e}")
            return False
    
    def initialize_sheets(self) -> bool:
        """Initialize Google Sheets with required worksheets and headers."""
        if self.connection is None:
            return False
        
        try:
            # Initialize Inventory worksheet
            inventory_headers = [
                "location_name", "item_name", "item_type", "quantity", 
                "capacity", "last_updated"
            ]
            self._ensure_worksheet_exists("Inventory", inventory_headers)
            
            # Initialize Tasks worksheet  
            task_headers = [
                "task_id", "name", "task_type", "priority", "status",
                "created_at", "updated_at", "assigned_to", "description"
            ]
            self._ensure_worksheet_exists("Tasks", task_headers)
            
            # Initialize Locations worksheet
            location_headers = [
                "name", "region", "facility_type", "position_x", "position_y"
            ]
            self._ensure_worksheet_exists("Locations", location_headers)
            
            # Initialize Analytics worksheet
            analytics_headers = [
                "metric_name", "metric_value", "timestamp", "metadata"
            ]
            self._ensure_worksheet_exists("Analytics", analytics_headers)
            
            self.logger.info("Successfully initialized Google Sheets")
            return True
            
        except Exception as e:
            self._last_error = f"Failed to initialize sheets: {str(e)}"
            self.logger.error(self._last_error)
            return False
    
    def _ensure_worksheet_exists(self, worksheet_name: str, headers: List[str]) -> None:
        """Ensure a worksheet exists with the required headers."""
        try:
            # Try to read the worksheet to see if it exists
            df = self.connection.read(worksheet=worksheet_name, ttl=0)
            
            # Check if headers match - if not, recreate with proper headers
            if list(df.columns) != headers:
                self.logger.info(f"Updating headers for worksheet {worksheet_name}")
                # Create new DataFrame with headers
                empty_df = pd.DataFrame(columns=headers)
                self.connection.update(worksheet=worksheet_name, data=empty_df)
                
        except Exception:
            # Worksheet doesn't exist, create it
            self.logger.info(f"Creating new worksheet: {worksheet_name}")
            empty_df = pd.DataFrame(columns=headers)
            self.connection.create(worksheet=worksheet_name, data=empty_df)
    
    def load_inventory_data(self) -> List[Location]:
        """Load inventory data from Google Sheets."""
        if self.connection is None:
            self.logger.warning("No connection - returning sample data")
            return SAMPLE_LOCATIONS.copy()
        
        try:
            # Load inventory data
            inventory_df = self.connection.read(worksheet="Inventory", ttl=60)
            locations_df = self.connection.read(worksheet="Locations", ttl=300)
            
            # If sheets are empty, populate with sample data
            if inventory_df.empty or locations_df.empty:
                self.logger.info("Empty sheets detected - populating with sample data")
                self.save_inventory_data(SAMPLE_LOCATIONS)
                return SAMPLE_LOCATIONS.copy()
            
            # Convert DataFrames back to Location objects
            locations = self._dataframes_to_locations(inventory_df, locations_df)
            self.logger.info(f"Loaded {len(locations)} locations from Google Sheets")
            return locations
            
        except Exception as e:
            self._last_error = f"Failed to load inventory: {str(e)}"
            self.logger.error(self._last_error)
            return SAMPLE_LOCATIONS.copy()
    
    def save_inventory_data(self, locations: List[Location]) -> bool:
        """Save inventory data to Google Sheets."""
        if self.connection is None:
            return False
        
        try:
            # Convert locations to DataFrames
            inventory_df, locations_df = self._locations_to_dataframes(locations)
            
            # Update both worksheets
            self.connection.update(worksheet="Inventory", data=inventory_df)
            self.connection.update(worksheet="Locations", data=locations_df)
            
            self.logger.info(f"Saved {len(locations)} locations to Google Sheets")
            return True
            
        except Exception as e:
            self._last_error = f"Failed to save inventory: {str(e)}"
            self.logger.error(self._last_error)
            return False
    
    def load_tasks(self) -> List[Task]:
        """Load tasks from Google Sheets."""
        if self.connection is None:
            return []
        
        try:
            tasks_df = self.connection.read(worksheet="Tasks", ttl=60)
            
            if tasks_df.empty:
                return []
            
            tasks = []
            for _, row in tasks_df.iterrows():
                task = Task(
                    task_id=str(row['task_id']),
                    name=str(row['name']),
                    task_type=str(row['task_type']),
                    priority=str(row['priority']),
                    status=TaskStatus(row['status']),
                    created_at=pd.to_datetime(row['created_at']),
                    updated_at=pd.to_datetime(row['updated_at']),
                    assigned_to=str(row['assigned_to']) if pd.notna(row['assigned_to']) else None,
                    description=str(row['description'])
                )
                tasks.append(task)
            
            self.logger.info(f"Loaded {len(tasks)} tasks from Google Sheets")
            return tasks
            
        except Exception as e:
            self._last_error = f"Failed to load tasks: {str(e)}"
            self.logger.error(self._last_error)
            return []
    
    def save_tasks(self, tasks: List[Task]) -> bool:
        """Save tasks to Google Sheets."""
        if self.connection is None:
            return False
        
        try:
            # Convert tasks to DataFrame
            tasks_data = []
            for task in tasks:
                task_dict = asdict(task)
                task_dict['status'] = task.status.value
                task_dict['created_at'] = task.created_at.isoformat()
                task_dict['updated_at'] = task.updated_at.isoformat()
                tasks_data.append(task_dict)
            
            tasks_df = pd.DataFrame(tasks_data)
            self.connection.update(worksheet="Tasks", data=tasks_df)
            
            self.logger.info(f"Saved {len(tasks)} tasks to Google Sheets")
            return True
            
        except Exception as e:
            self._last_error = f"Failed to save tasks: {str(e)}"
            self.logger.error(self._last_error)
            return False
    
    def log_analytics_metric(self, metric_name: str, metric_value: Union[int, float, str], 
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Log an analytics metric to Google Sheets."""
        if self.connection is None:
            return False
        
        try:
            # Read existing analytics data
            analytics_df = self.connection.read(worksheet="Analytics", ttl=0)
            
            # Create new metric row
            new_metric = {
                'metric_name': metric_name,
                'metric_value': metric_value,
                'timestamp': datetime.now().isoformat(),
                'metadata': json.dumps(metadata) if metadata else ""
            }
            
            # Append to existing data
            new_row_df = pd.DataFrame([new_metric])
            updated_df = pd.concat([analytics_df, new_row_df], ignore_index=True)
            
            # Keep only last 1000 metrics to avoid sheet bloat
            if len(updated_df) > 1000:
                updated_df = updated_df.tail(1000)
            
            self.connection.update(worksheet="Analytics", data=updated_df)
            return True
            
        except Exception as e:
            self._last_error = f"Failed to log metric: {str(e)}"
            self.logger.error(self._last_error)
            return False
    
    def get_analytics_metrics(self, metric_name: Optional[str] = None, 
                            hours_back: int = 24) -> pd.DataFrame:
        """Get analytics metrics from Google Sheets."""
        if self.connection is None:
            return pd.DataFrame()
        
        try:
            analytics_df = self.connection.read(worksheet="Analytics", ttl=60)
            
            if analytics_df.empty:
                return pd.DataFrame()
            
            # Convert timestamp column
            analytics_df['timestamp'] = pd.to_datetime(analytics_df['timestamp'])
            
            # Filter by time range
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            analytics_df = analytics_df[analytics_df['timestamp'] >= cutoff_time]
            
            # Filter by metric name if specified
            if metric_name:
                analytics_df = analytics_df[analytics_df['metric_name'] == metric_name]
            
            return analytics_df
            
        except Exception as e:
            self._last_error = f"Failed to get analytics: {str(e)}"
            self.logger.error(self._last_error)
            return pd.DataFrame()
    
    def _locations_to_dataframes(self, locations: List[Location]) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Convert Location objects to inventory and locations DataFrames."""
        inventory_data = []
        locations_data = []
        
        for location in locations:
            # Location data
            locations_data.append({
                'name': location.name,
                'region': location.region,
                'facility_type': location.facility_type.value,
                'position_x': location.position[0],
                'position_y': location.position[1]
            })
            
            # Inventory data
            for item_name, inventory_state in location.inventory.items():
                inventory_data.append({
                    'location_name': location.name,
                    'item_name': inventory_state.item.name,
                    'item_type': inventory_state.item.item_type.value,
                    'quantity': inventory_state.quantity,
                    'capacity': inventory_state.capacity,
                    'last_updated': datetime.now().isoformat()
                })
        
        inventory_df = pd.DataFrame(inventory_data)
        locations_df = pd.DataFrame(locations_data)
        
        return inventory_df, locations_df
    
    def _dataframes_to_locations(self, inventory_df: pd.DataFrame, 
                                locations_df: pd.DataFrame) -> List[Location]:
        """Convert inventory and locations DataFrames back to Location objects."""
        locations = []
        items_dict = {item.name: item for item in FOXHOLE_ITEMS}
        
        for _, location_row in locations_df.iterrows():
            # Create location
            location = Location(
                name=location_row['name'],
                region=location_row['region'],
                facility_type=FacilityType(location_row['facility_type']),
                position=(location_row['position_x'], location_row['position_y'])
            )
            
            # Add inventory for this location
            location_inventory = inventory_df[inventory_df['location_name'] == location.name]
            for _, inv_row in location_inventory.iterrows():
                item_name = inv_row['item_name']
                if item_name in items_dict:
                    item = items_dict[item_name]
                else:
                    # Create item if not in predefined list
                    item = Item(
                        name=item_name,
                        item_type=ItemType(inv_row['item_type'])
                    )
                
                inventory_state = InventoryState(
                    item=item,
                    quantity=int(inv_row['quantity']),
                    capacity=int(inv_row['capacity'])
                )
                location.inventory[item_name] = inventory_state
            
            locations.append(location)
        
        return locations


# Global instance for the backend
_backend_instance = None

def get_gsheets_backend() -> GSheetsDataBackend:
    """Get the global Google Sheets backend instance."""
    global _backend_instance
    if _backend_instance is None:
        _backend_instance = GSheetsDataBackend()
    return _backend_instance