"""Unit tests for the TaskGenerationService's priority functionality."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.task import Task, TaskPriority, TaskStatus, TaskType
from src.models.inventory import Inventory
from src.models.item import Item
from src.models.location import Location
from src.services.task_generation_service import TaskGenerationService
from src.services.task_service import TaskService
from src.database.database_manager import DatabaseManager
from src.config.priority_config import (
    get_location_priority,
    get_item_priority,
    get_deficit_multiplier,
    get_time_multiplier,
    round_to_capacity,
    get_truck_capacity,
    get_available_truck_types
)

class TestTaskGenerationServicePriority:
    """Test suite for TaskGenerationService priority functionality."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        manager = AsyncMock(spec=DatabaseManager)
        manager.get_session.return_value.__aenter__.return_value = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_task_service(self):
        """Create a mock task service."""
        return AsyncMock(spec=TaskService)
    
    @pytest.fixture
    def task_generation_service(self, mock_db_manager, mock_task_service):
        """Create a TaskGenerationService instance with mocked dependencies."""
        return TaskGenerationService(mock_db_manager, mock_task_service)
    
    def test_set_default_truck_type(self, task_generation_service):
        """Test setting default truck type."""
        # Test valid truck type
        task_generation_service.set_default_truck_type("landrunner")
        assert task_generation_service.default_truck_type == "landrunner"
        
        # Test invalid truck type
        task_generation_service.set_default_truck_type("invalid")
        assert task_generation_service.default_truck_type == "standard"
    
    @pytest.mark.asyncio
    async def test_check_inventory_levels_priority_calculation(self, task_generation_service, mock_db_manager, mock_task_service):
        """Test priority calculation during inventory level checks."""
        # Arrange
        location = Location(
            id="test-loc",
            name="Test Location",
            building_type="BUNKER_BASE"
        )
        
        item = Item(
            id="test-item",
            name="Test Item",
            category="CRITICAL",
            target_quantity=100
        )
        
        inventory = Inventory(
            id="test-inv",
            location_id="test-loc",
            item_id="test-item",
            quantity=10  # 90% deficit
        )
        
        session = mock_db_manager.get_session.return_value.__aenter__.return_value
        session.execute = AsyncMock(side_effect=[
            MagicMock(scalars=MagicMock(return_value=[location])),
            MagicMock(scalars=MagicMock(return_value=[inventory])),
            MagicMock(scalars=MagicMock(return_value=[item]))
        ])
        
        # Test with standard truck
        task_generation_service.set_default_truck_type("standard")
        await task_generation_service._check_inventory_levels()
        
        # Assert
        mock_task_service.create_task.assert_called_once()
        call_args = mock_task_service.create_task.call_args[1]
        
        # Verify priority components
        assert call_args["base_priority"] == get_item_priority("CRITICAL")
        assert call_args["deficit_severity_bonus"] > 0  # Should have deficit bonus
        assert call_args["location_importance_bonus"] > 0  # Should have location bonus
        assert call_args["is_ftl"] == 0  # Not FTL (quantity is 90)
        assert call_args["is_fcl"] == 0  # Not FCL (quantity is 90)
        
        # Test with Landrunner truck
        mock_task_service.reset_mock()
        task_generation_service.set_default_truck_type("landrunner")
        await task_generation_service._check_inventory_levels()
        
        # Assert
        mock_task_service.create_task.assert_called_once()
        call_args = mock_task_service.create_task.call_args[1]
        assert call_args["is_ftl"] == 0  # Not FTL (quantity is 90)
        assert call_args["is_fcl"] == 0  # Not FCL (quantity is 90)
    
    @pytest.mark.asyncio
    async def test_ftl_detection_with_different_trucks(self, task_generation_service, mock_db_manager, mock_task_service):
        """Test FTL detection with different truck types."""
        # Arrange
        location = Location(
            id="test-loc",
            name="Test Location",
            building_type="BUNKER_BASE"
        )
        
        item = Item(
            id="test-item",
            name="Test Item",
            category="CRITICAL",
            target_quantity=15  # Exactly one standard truck load
        )
        
        inventory = Inventory(
            id="test-inv",
            location_id="test-loc",
            item_id="test-item",
            quantity=0  # Full deficit
        )
        
        session = mock_db_manager.get_session.return_value.__aenter__.return_value
        session.execute = AsyncMock(side_effect=[
            MagicMock(scalars=MagicMock(return_value=[location])),
            MagicMock(scalars=MagicMock(return_value=[inventory])),
            MagicMock(scalars=MagicMock(return_value=[item]))
        ])
        
        # Test with standard truck
        task_generation_service.set_default_truck_type("standard")
        await task_generation_service._check_inventory_levels()
        
        # Assert
        mock_task_service.create_task.assert_called_once()
        call_args = mock_task_service.create_task.call_args[1]
        assert call_args["is_ftl"] == 1  # Should be FTL for standard truck
        assert call_args["is_fcl"] == 0
        
        # Test with Landrunner truck
        mock_task_service.reset_mock()
        task_generation_service.set_default_truck_type("landrunner")
        await task_generation_service._check_inventory_levels()
        
        # Assert
        mock_task_service.create_task.assert_called_once()
        call_args = mock_task_service.create_task.call_args[1]
        assert call_args["is_ftl"] == 0  # Should not be FTL for Landrunner
        assert call_args["is_fcl"] == 0
    
    @pytest.mark.asyncio
    async def test_determine_task_type(self, task_generation_service):
        """Test task type determination based on location."""
        # Arrange
        item = Item(
            id="test-item",
            name="Test Item",
            category="CRITICAL",
            target_quantity=100
        )
        
        # Test different location types
        location_types = {
            "FACTORY": TaskType.QUEUE_PRODUCTION,
            "MPF": TaskType.QUEUE_PRODUCTION,
            "BUNKER_BASE": TaskType.TRANSPORT_LAST_MILE,
            "FOB": TaskType.TRANSPORT_LAST_MILE,
            "STORAGE_DEPOT": TaskType.TRANSPORT
        }
        
        # Act & Assert
        for building_type, expected_type in location_types.items():
            location = Location(
                id=f"test-loc-{building_type}",
                name="Test Location",
                building_type=building_type
            )
            
            task_type = task_generation_service._determine_task_type(item, location)
            assert task_type == expected_type
    
    @pytest.mark.asyncio
    async def test_find_source_location(self, task_generation_service, mock_db_manager):
        """Test source location finding with priority consideration."""
        # Arrange
        item = Item(
            id="test-item",
            name="Test Item",
            category="CRITICAL",
            target_quantity=100
        )
        
        destination = Location(
            id="test-dest",
            name="Test Destination",
            building_type="BUNKER_BASE"
        )
        
        potential_sources = [
            Location(id="source-1", name="Source 1", building_type="FACTORY"),
            Location(id="source-2", name="Source 2", building_type="MPF"),
            Location(id="source-3", name="Source 3", building_type="STORAGE_DEPOT")
        ]
        
        session = mock_db_manager.get_session.return_value.__aenter__.return_value
        session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=potential_sources)))
        
        # Act
        source = await task_generation_service._find_source_location(session, item, destination)
        
        # Assert
        assert source in potential_sources
        assert source.building_type in ["FACTORY", "MPF", "STORAGE_DEPOT", "SEAPORT"]
    
    def test_estimate_task_time(self, task_generation_service):
        """Test task time estimation based on quantity and category."""
        # Arrange
        item = Item(
            id="test-item",
            name="Test Item",
            category="CRITICAL",
            target_quantity=100
        )
        
        # Test different quantities
        test_cases = [
            (15, 30),   # FTL
            (60, 70),   # FCL
            (100, 90)   # Partial
        ]
        
        # Act & Assert
        for quantity, expected_time in test_cases:
            time = task_generation_service._estimate_task_time(item, quantity)
            assert time >= expected_time  # Should be at least the expected time
    
    @pytest.mark.asyncio
    async def test_get_inventory_status(self, task_generation_service, mock_db_manager):
        """Test inventory status retrieval with priority information."""
        # Arrange
        inventory = Inventory(
            id="test-inv",
            location_id="test-loc",
            item_id="test-item",
            quantity=10
        )
        
        item = Item(
            id="test-item",
            name="Test Item",
            category="CRITICAL",
            target_quantity=100
        )
        
        location = Location(
            id="test-loc",
            name="Test Location",
            building_type="BUNKER_BASE"
        )
        
        session = mock_db_manager.get_session.return_value.__aenter__.return_value
        session.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[(inventory, item, location)])))
        
        # Act
        status_list = await task_generation_service.get_inventory_status()
        
        # Assert
        assert len(status_list) == 1
        status = status_list[0]
        assert status["deficit_percentage"] == 0.9  # 90% deficit
        assert status["status"] == "Critical"  # Should be critical due to high deficit
        assert status["location_name"] == "Test Location"
        assert status["item_name"] == "Test Item"
        assert status["item_category"] == "CRITICAL" 