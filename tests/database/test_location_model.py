"""
Tests for the Location model.
"""
import pytest
from sqlalchemy.exc import IntegrityError

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


def test_create_location(db_session, regiment, sample_location_data):
    """Test creating a location."""
    location = Location(regiment_id=regiment.id, **sample_location_data)
    db_session.add(location)
    db_session.commit()

    assert location.id is not None
    assert location.name == sample_location_data["name"]
    assert location.location_type == sample_location_data["location_type"]
    assert location.coordinates == sample_location_data["coordinates"]
    assert location.created_at is not None
    assert location.updated_at is not None


def test_location_type_validation(db_session, regiment, sample_location_data):
    """Test that location_type must be a valid LocationType enum value."""
    # Try to create location with invalid type
    invalid_data = sample_location_data.copy()
    invalid_data["location_type"] = "INVALID_TYPE"
    
    location = Location(regiment_id=regiment.id, **invalid_data)
    db_session.add(location)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_location_required_fields(db_session, regiment):
    """Test that required fields raise appropriate errors when missing."""
    # Try to create location without name
    location = Location(
        regiment_id=regiment.id,
        location_type=LocationType.FRONTLINE_HUB,
        coordinates="F5-2"
    )
    db_session.add(location)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Try to create location without location_type
    location = Location(
        regiment_id=regiment.id,
        name="Test Location",
        coordinates="F5-2"
    )
    db_session.add(location)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_location_regiment_relationship(db_session, regiment, sample_location_data):
    """Test location's relationship with regiment."""
    location = Location(regiment_id=regiment.id, **sample_location_data)
    db_session.add(location)
    db_session.commit()

    # Test relationship from location to regiment
    assert location.regiment.id == regiment.id
    assert location.regiment.name == regiment.name

    # Test relationship from regiment to location
    assert len(regiment.locations) == 1
    assert regiment.locations[0].id == location.id


def test_location_managed_by_role(db_session, regiment, role, sample_location_data):
    """Test location's relationship with managing role."""
    location = Location(
        regiment_id=regiment.id,
        managed_by_role_id=role.id,
        **sample_location_data
    )
    db_session.add(location)
    db_session.commit()

    assert location.managed_by_role.id == role.id
    assert location.managed_by_role.name == role.name


def test_location_source_relationships(db_session, regiment, sample_location_data):
    """Test location's source/target relationships."""
    # Create source and target locations
    source = Location(regiment_id=regiment.id, name="Source", location_type=LocationType.BACKLINE_HUB, coordinates="F5-1")
    target = Location(regiment_id=regiment.id, **sample_location_data)
    db_session.add_all([source, target])
    db_session.commit()

    # Create relationship
    target.source_locations.append(source)
    db_session.commit()

    # Test relationships
    assert len(target.source_locations) == 1
    assert target.source_locations[0].id == source.id
    assert len(source.target_locations) == 1
    assert source.target_locations[0].id == target.id


def test_location_inventory_relationship(db_session, regiment, sample_location_data, sample_item_data):
    """Test location's relationship with inventory."""
    # Create location and item
    location = Location(regiment_id=regiment.id, **sample_location_data)
    item = Item(**sample_item_data)
    db_session.add_all([location, item])
    db_session.commit()

    # Create inventory
    inventory = Inventory(
        location_id=location.id,
        item_id=item.id,
        quantity=100,
        last_updated=location.created_at,
        reported_by_user_id=1  # This would normally be a valid user ID
    )
    db_session.add(inventory)
    db_session.commit()

    assert len(location.inventories) == 1
    assert location.inventories[0].quantity == 100
    assert location.inventories[0].item.id == item.id


def test_location_buffer_relationship(db_session, regiment, sample_location_data, sample_item_data, sample_location_buffer_data):
    """Test location's relationship with location buffers."""
    # Create location and item
    location = Location(regiment_id=regiment.id, **sample_location_data)
    item = Item(**sample_item_data)
    db_session.add_all([location, item])
    db_session.commit()

    # Create location buffer
    buffer = LocationBuffer(
        location_id=location.id,
        item_id=item.id,
        **sample_location_buffer_data
    )
    db_session.add(buffer)
    db_session.commit()

    assert len(location.location_buffers) == 1
    assert location.location_buffers[0].target_quantity == sample_location_buffer_data["target_quantity"]
    assert location.location_buffers[0].item.id == item.id


def test_location_task_relationships(db_session, regiment, sample_location_data, sample_item_data, sample_task_data):
    """Test location's relationships with tasks (as source and target)."""
    # Create locations and item
    source = Location(regiment_id=regiment.id, name="Source", location_type=LocationType.BACKLINE_HUB, coordinates="F5-1")
    target = Location(regiment_id=regiment.id, **sample_location_data)
    item = Item(**sample_item_data)
    db_session.add_all([source, target, item])
    db_session.commit()

    # Create task
    task = Task(
        source_location_id=source.id,
        target_location_id=target.id,
        item_id=item.id,
        **sample_task_data
    )
    db_session.add(task)
    db_session.commit()

    # Test relationships
    assert len(source.source_tasks) == 1
    assert source.source_tasks[0].id == task.id
    assert len(target.target_tasks) == 1
    assert target.target_tasks[0].id == task.id


def test_location_cascade_delete(db_session, regiment, sample_location_data, sample_item_data):
    """Test that deleting a location cascades to related entities."""
    # Create location and item
    location = Location(regiment_id=regiment.id, **sample_location_data)
    item = Item(**sample_item_data)
    db_session.add_all([location, item])
    db_session.commit()

    # Create inventory and buffer
    inventory = Inventory(
        location_id=location.id,
        item_id=item.id,
        quantity=100,
        last_updated=location.created_at,
        reported_by_user_id=1
    )
    buffer = LocationBuffer(
        location_id=location.id,
        item_id=item.id,
        target_quantity=1000,
        critical_threshold_percent=25,
        priority_score=3
    )
    db_session.add_all([inventory, buffer])
    db_session.commit()

    # Store IDs for verification
    inventory_id = inventory.id
    buffer_id = buffer.id

    # Delete location
    db_session.delete(location)
    db_session.commit()

    # Verify cascade delete
    assert db_session.query(Inventory).filter_by(id=inventory_id).first() is None
    assert db_session.query(LocationBuffer).filter_by(location_id=location.id, item_id=item.id).first() is None 