"""
Tests for database models.
"""
import pytest
from sqlalchemy.exc import IntegrityError

from src.database.models import Regiment, Channel, Role


def test_create_regiment(db_session, sample_regiment_data):
    """Test creating a regiment."""
    regiment = Regiment(**sample_regiment_data)
    db_session.add(regiment)
    db_session.commit()

    assert regiment.id is not None
    assert regiment.regiment_id == sample_regiment_data["regiment_id"]
    assert regiment.name == sample_regiment_data["name"]
    assert regiment.created_at is not None
    assert regiment.updated_at is not None


def test_regiment_unique_regiment_id(db_session, sample_regiment_data):
    """Test that regiment_id must be unique."""
    # Create first regiment
    regiment1 = Regiment(**sample_regiment_data)
    db_session.add(regiment1)
    db_session.commit()

    # Try to create second regiment with same regiment_id
    regiment2 = Regiment(**sample_regiment_data)
    db_session.add(regiment2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_regiment_relationships(db_session, sample_regiment_data):
    """Test regiment relationships with channels and roles."""
    # Create regiment
    regiment = Regiment(**sample_regiment_data)
    db_session.add(regiment)
    db_session.commit()

    # Create channel
    channel = Channel(
        regiment_id=regiment.id,
        channel_id="987654321",
        name="test-channel",
        channel_type="text"
    )
    db_session.add(channel)

    # Create role
    role = Role(
        regiment_id=regiment.id,
        role_id="456789123",
        name="Test Role",
        permissions=0
    )
    db_session.add(role)
    db_session.commit()

    # Test relationships
    assert len(regiment.channels) == 1
    assert regiment.channels[0].channel_id == "987654321"
    assert len(regiment.roles) == 1
    assert regiment.roles[0].role_id == "456789123"


def test_regiment_cascade_delete(db_session, sample_regiment_data):
    """Test that deleting a regiment cascades to channels and roles."""
    # Create regiment with channel and role
    regiment = Regiment(**sample_regiment_data)
    db_session.add(regiment)
    db_session.commit()

    channel = Channel(
        regiment_id=regiment.id,
        channel_id="987654321",
        name="test-channel",
        channel_type="text"
    )
    db_session.add(channel)

    role = Role(
        regiment_id=regiment.id,
        role_id="456789123",
        name="Test Role",
        permissions=0
    )
    db_session.add(role)
    db_session.commit()

    # Get IDs for later verification
    channel_id = channel.id
    role_id = role.id

    # Delete regiment
    db_session.delete(regiment)
    db_session.commit()

    # Verify cascade delete
    assert db_session.query(Channel).filter_by(id=channel_id).first() is None
    assert db_session.query(Role).filter_by(id=role_id).first() is None


def test_regiment_required_fields(db_session):
    """Test that required fields raise appropriate errors when missing."""
    # Try to create regiment without regiment_id
    regiment = Regiment(name="Test Regiment")
    db_session.add(regiment)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Try to create regiment without name
    regiment = Regiment(regiment_id="123456789")
    db_session.add(regiment)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_regiment_timestamps(db_session, sample_regiment_data):
    """Test that timestamps are automatically set and updated."""
    # Create regiment
    regiment = Regiment(**sample_regiment_data)
    db_session.add(regiment)
    db_session.commit()

    # Store initial timestamps
    created_at = regiment.created_at
    updated_at = regiment.updated_at

    # Update regiment
    regiment.name = "Updated Regiment Name"
    db_session.commit()

    # Verify timestamps
    assert regiment.created_at == created_at  # Should not change
    assert regiment.updated_at > updated_at  # Should be updated 