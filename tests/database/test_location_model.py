"""
Tests for the Location model and its relationships.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from src.database.models import (
    Location,
    LocationType,
    Regiment,
    Role,
    Item,
    Inventory,
    LocationBuffer,
    Task
)


@pytest.fixture
def regiment(db_session, sample_regiment_data):
    """Create a test regiment."""
    regiment = Regiment(**sample_regiment_data)
    db_session.add(regiment)
    db_session.commit()
    return regiment


@pytest.fixture
def role(db_session, regiment):
    """Create a test role."""
    role = Role(
        regiment_id=regiment.id,
        role_id="456789123",
        name="Test Role",
        permissions=0
    )
    db_session.add(role)
    db_session.commit()
    return role


@pytest.mark.asyncio
async def test_create_location(async_session, regiment):
    """Test creating a basic location."""
    # Create test location
    location = Location(
        regiment_id=regiment.id,
        name="Test Location",
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-2"
    )
    
    # Add to session
    async_session.add(location)
    await async_session.commit()
    
    # Retrieve location
    result = await async_session.execute(select(Location).where(Location.name == "Test Location"))
    retrieved_location = result.scalar_one()
    
    # Verify attributes
    assert retrieved_location.name == "Test Location"
    assert retrieved_location.location_type == LocationType.FRONTLINE_HUB
    assert retrieved_location.coordinates == "F5-2"
    assert retrieved_location.regiment_id == regiment.id


def test_location_type_validation(db_session, regiment):
    """Test that location_type must be a valid LocationType enum value."""
    location = Location(
        regiment_id=regiment.id,
        name="Test Location",
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-2"
    )
    db_session.add(location)
    db_session.commit()

    assert location.location_type == LocationType.FRONTLINE_HUB


@pytest.mark.asyncio
async def test_location_required_fields(async_session, regiment):
    """Test that required fields raise appropriate errors when missing."""
    # Try to create location without name
    location = Location(
        regiment_id=regiment.id,
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-2"
    )
    async_session.add(location)
    with pytest.raises(IntegrityError):
        await async_session.commit()
    await async_session.rollback()

    # Try to create location without location_type
    location = Location(
        regiment_id=regiment.id,
        name="Test Location",
        coordinates="F5-2"
    )
    async_session.add(location)
    with pytest.raises(IntegrityError):
        await async_session.commit()
    await async_session.rollback()


def test_location_regiment_relationship(db_session, regiment):
    """Test the relationship between Location and Regiment."""
    location = Location(
        regiment_id=regiment.id,
        name="Test Location",
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-2"
    )
    db_session.add(location)
    db_session.commit()

    assert location.regiment == regiment
    assert location in regiment.locations


def test_location_managed_by_role(db_session, regiment, role):
    """Test the relationship between Location and Role."""
    location = Location(
        regiment_id=regiment.id,
        name="Test Location",
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-2",
        managed_by_role_id=role.id
    )
    db_session.add(location)
    db_session.commit()

    assert location.managed_by_role == role


@pytest.mark.asyncio
async def test_location_source_relationships(async_session, regiment):
    """Test the relationships between source and target locations."""
    # Create source and target locations
    source_location = Location(
        regiment_id=regiment.id,
        name="Source Location",
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-2"
    )
    target_location = Location(
        regiment_id=regiment.id,
        name="Target Location",
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-3"
    )
    
    # Add to session
    async_session.add_all([source_location, target_location])
    await async_session.commit()
    
    # Create source relationship
    source_location.target_locations.append(target_location)
    await async_session.commit()
    
    # Retrieve locations
    result = await async_session.execute(select(Location).where(Location.name == "Source Location"))
    retrieved_source = result.scalar_one()
    
    # Verify relationships
    assert len(retrieved_source.target_locations) == 1
    assert retrieved_source.target_locations[0].name == "Target Location"
    
    result = await async_session.execute(select(Location).where(Location.name == "Target Location"))
    retrieved_target = result.scalar_one()
    assert len(retrieved_target.source_locations) == 1
    assert retrieved_target.source_locations[0].name == "Source Location"


@pytest.mark.asyncio
async def test_location_inventory_relationship(async_session, regiment):
    """Test the relationship between locations and inventories."""
    # Create location
    location = Location(
        regiment_id=regiment.id,
        name="Test Location",
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-2"
    )
    
    # Add to session
    async_session.add(location)
    await async_session.commit()
    
    # Create inventory
    inventory = Inventory(
        location_id=location.id,
        item_id=1,  # Assuming item exists
        quantity=100,
        last_updated=datetime.utcnow(),
        reported_by_user_id=1  # Assuming user exists
    )
    
    # Add to session
    async_session.add(inventory)
    await async_session.commit()
    
    # Retrieve location
    result = await async_session.execute(select(Location).where(Location.name == "Test Location"))
    retrieved_location = result.scalar_one()
    
    # Verify relationship
    assert len(retrieved_location.inventories) == 1
    assert retrieved_location.inventories[0].quantity == 100


@pytest.mark.asyncio
async def test_location_buffer_relationship(async_session, regiment):
    """Test the relationship between locations and buffers."""
    # Create location
    location = Location(
        regiment_id=regiment.id,
        name="Test Location",
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-2"
    )
    
    # Add to session
    async_session.add(location)
    await async_session.commit()
    
    # Create buffer
    buffer = LocationBuffer(
        location_id=location.id,
        item_id=1,  # Assuming item exists
        target_quantity=1000,
        critical_threshold_percent=20,
        priority_score=1
    )
    
    # Add to session
    async_session.add(buffer)
    await async_session.commit()
    
    # Retrieve location
    result = await async_session.execute(select(Location).where(Location.name == "Test Location"))
    retrieved_location = result.scalar_one()
    
    # Verify relationship
    assert len(retrieved_location.location_buffers) == 1
    assert retrieved_location.location_buffers[0].target_quantity == 1000


@pytest.mark.asyncio
async def test_location_task_relationships(async_session, regiment):
    """Test the relationships between locations and tasks."""
    # Create source and target locations
    source_location = Location(
        regiment_id=regiment.id,
        name="Source Location",
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-2"
    )
    target_location = Location(
        regiment_id=regiment.id,
        name="Target Location",
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-3"
    )
    
    # Add to session
    async_session.add_all([source_location, target_location])
    await async_session.commit()
    
    # Create task
    task = Task(
        task_type=TaskType.TRANSPORT,
        item_id=1,  # Assuming item exists
        quantity=100,
        status=TaskStatus.PENDING,
        priority_score=1,
        source_location_id=source_location.id,
        target_location_id=target_location.id,
        urgency=UrgencyLevel.NORMAL
    )
    
    # Add to session
    async_session.add(task)
    await async_session.commit()
    
    # Retrieve locations
    result = await async_session.execute(select(Location).where(Location.name == "Source Location"))
    retrieved_source = result.scalar_one()
    assert len(retrieved_source.source_tasks) == 1
    
    result = await async_session.execute(select(Location).where(Location.name == "Target Location"))
    retrieved_target = result.scalar_one()
    assert len(retrieved_target.target_tasks) == 1


@pytest.mark.asyncio
async def test_location_cascade_delete(async_session, regiment):
    """Test that deleting a location cascades to related entities."""
    # Create location
    location = Location(
        regiment_id=regiment.id,
        name="Test Location",
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-2"
    )
    
    # Add to session
    async_session.add(location)
    await async_session.commit()
    
    # Create related entities
    inventory = Inventory(
        location_id=location.id,
        item_id=1,
        quantity=100,
        last_updated=datetime.utcnow(),
        reported_by_user_id=1
    )
    buffer = LocationBuffer(
        location_id=location.id,
        item_id=1,
        target_quantity=1000,
        critical_threshold_percent=20,
        priority_score=1
    )
    
    # Add to session
    async_session.add_all([inventory, buffer])
    await async_session.commit()
    
    # Delete location
    await async_session.delete(location)
    await async_session.commit()
    
    # Verify cascade delete
    result = await async_session.execute(select(Inventory).where(Inventory.location_id == location.id))
    assert result.scalar_one_or_none() is None
    
    result = await async_session.execute(select(LocationBuffer).where(LocationBuffer.location_id == location.id))
    assert result.scalar_one_or_none() is None 