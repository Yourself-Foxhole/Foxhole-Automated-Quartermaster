"""
Tests for the Item model and its relationships.
"""

import pytest
from sqlalchemy import select
from src.models.item import Item, ItemBuildingTarget

@pytest.mark.asyncio
async def test_create_item(db_session):
    """Test creating a basic item."""
    # Create test item
    item = Item(
        id="test_item",
        name="Test Item",
        category="Supplies",
        description="A test item",
        importance=4
    )
    
    # Add to session
    db_session.add(item)
    await db_session.commit()
    
    # Retrieve item
    result = await db_session.execute(select(Item).where(Item.id == "test_item"))
    retrieved_item = result.scalar_one()
    
    # Verify attributes
    assert retrieved_item.id == "test_item"
    assert retrieved_item.name == "Test Item"
    assert retrieved_item.category == "Supplies"
    assert retrieved_item.description == "A test item"
    assert retrieved_item.importance == 4
    assert not retrieved_item.can_be_produced
    assert retrieved_item.production_facility is None

@pytest.mark.asyncio
async def test_item_building_targets(db_session):
    """Test item-building target relationships."""
    # Create test item
    item = Item(
        id="test_item",
        name="Test Item",
        category="Supplies",
        description="A test item",
        importance=4
    )
    
    # Add building targets
    targets = [
        ItemBuildingTarget(
            item_id=item.id,
            building_type="Bunker",
            target_quantity=1000
        ),
        ItemBuildingTarget(
            item_id=item.id,
            building_type="Safehouse",
            target_quantity=500
        )
    ]
    item.building_targets.extend(targets)
    
    # Add to session
    db_session.add(item)
    await db_session.commit()
    
    # Retrieve item
    result = await db_session.execute(select(Item).where(Item.id == "test_item"))
    retrieved_item = result.scalar_one()
    
    # Verify building targets
    assert len(retrieved_item.building_targets) == 2
    assert retrieved_item.get_target_quantity("Bunker") == 1000
    assert retrieved_item.get_target_quantity("Safehouse") == 500
    assert retrieved_item.get_target_quantity("Factory") is None

@pytest.mark.asyncio
async def test_item_to_dict(db_session):
    """Test converting item to dictionary."""
    # Create test item with building targets
    item = Item(
        id="test_item",
        name="Test Item",
        category="Supplies",
        description="A test item",
        importance=4,
        can_be_produced=True,
        production_facility="Factory"
    )
    
    # Add building target
    target = ItemBuildingTarget(
        item_id=item.id,
        building_type="Bunker",
        target_quantity=1000
    )
    item.building_targets.append(target)
    
    # Convert to dictionary
    item_dict = item.to_dict()
    
    # Verify dictionary contents
    assert item_dict["id"] == "test_item"
    assert item_dict["name"] == "Test Item"
    assert item_dict["category"] == "Supplies"
    assert item_dict["description"] == "A test item"
    assert item_dict["importance"] == 4
    assert item_dict["can_be_produced"] is True
    assert item_dict["production_facility"] == "Factory"
    assert len(item_dict["building_targets"]) == 1
    assert item_dict["building_targets"][0]["building_type"] == "Bunker"
    assert item_dict["building_targets"][0]["target_quantity"] == 1000

@pytest.mark.asyncio
async def test_create_from_dict(db_session):
    """Test creating item from dictionary."""
    # Create item dictionary
    item_dict = {
        "id": "test_item",
        "name": "Test Item",
        "category": "Supplies",
        "description": "A test item",
        "importance": 4,
        "can_be_produced": True,
        "production_facility": "Factory",
        "building_targets": [
            {
                "building_type": "Bunker",
                "target_quantity": 1000
            }
        ]
    }
    
    # Create item from dictionary
    item = Item.from_dict(item_dict)
    
    # Add to session
    db_session.add(item)
    await db_session.commit()
    
    # Retrieve item
    result = await db_session.execute(select(Item).where(Item.id == "test_item"))
    retrieved_item = result.scalar_one()
    
    # Verify attributes
    assert retrieved_item.id == "test_item"
    assert retrieved_item.name == "Test Item"
    assert retrieved_item.category == "Supplies"
    assert retrieved_item.description == "A test item"
    assert retrieved_item.importance == 4
    assert retrieved_item.can_be_produced is True
    assert retrieved_item.production_facility == "Factory"
    assert len(retrieved_item.building_targets) == 1
    assert retrieved_item.building_targets[0].building_type == "Bunker"
    assert retrieved_item.building_targets[0].target_quantity == 1000 