"""
Tests for the Item model.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.item import Item, ItemBuildingTarget
from src.models.enums import ItemCategory, ProductionLocationType

@pytest.mark.asyncio
async def test_create_item(async_session: AsyncSession):
    """Test creating a basic item."""
    item = Item(
        name="7.62mm",
        category=ItemCategory.AMMUNITION,
        description="Standard rifle ammunition",
        importance=1,
        can_be_produced=True,
        production_facility=ProductionLocationType.FACTORY
    )
    
    async_session.add(item)
    await async_session.commit()
    
    # Verify item was created
    assert item.id is not None
    assert item.name == "7.62mm"
    assert item.category == ItemCategory.AMMUNITION
    assert item.description == "Standard rifle ammunition"
    assert item.importance == 1
    assert item.can_be_produced is True
    assert item.production_facility == ProductionLocationType.FACTORY

@pytest.mark.asyncio
async def test_item_building_targets(async_session: AsyncSession):
    """Test item building target relationships."""
    item = Item(
        name="7.62mm",
        category=ItemCategory.AMMUNITION,
        description="Standard rifle ammunition",
        importance=1,
        can_be_produced=True,
        production_facility=ProductionLocationType.FACTORY
    )
    
    # Add building targets
    target1 = ItemBuildingTarget(
        building_type=ProductionLocationType.FACTORY,
        target_quantity=1000
    )
    target2 = ItemBuildingTarget(
        building_type=ProductionLocationType.STORAGE_DEPOT,
        target_quantity=500
    )
    
    item.building_targets.extend([target1, target2])
    async_session.add(item)
    await async_session.commit()
    
    # Verify targets were created
    assert len(item.building_targets) == 2
    assert item.get_target_quantity(ProductionLocationType.FACTORY) == 1000
    assert item.get_target_quantity(ProductionLocationType.STORAGE_DEPOT) == 500
    assert item.get_target_quantity(ProductionLocationType.REFINERY) == 0  # Default for unknown building

@pytest.mark.asyncio
async def test_item_to_dict(async_session: AsyncSession):
    """Test converting item to dictionary."""
    item = Item(
        name="7.62mm",
        category=ItemCategory.AMMUNITION,
        description="Standard rifle ammunition",
        importance=1,
        can_be_produced=True,
        production_facility=ProductionLocationType.FACTORY
    )
    
    target = ItemBuildingTarget(
        building_type=ProductionLocationType.FACTORY,
        target_quantity=1000
    )
    item.building_targets.append(target)
    
    async_session.add(item)
    await async_session.commit()
    
    # Convert to dict
    item_dict = item.to_dict()
    
    # Verify dictionary contents
    assert item_dict["id"] == item.id
    assert item_dict["name"] == "7.62mm"
    assert item_dict["category"] == ItemCategory.AMMUNITION
    assert item_dict["description"] == "Standard rifle ammunition"
    assert item_dict["importance"] == 1
    assert item_dict["can_be_produced"] is True
    assert item_dict["production_facility"] == ProductionLocationType.FACTORY
    assert len(item_dict["building_targets"]) == 1
    assert item_dict["building_targets"][0]["building_type"] == ProductionLocationType.FACTORY
    assert item_dict["building_targets"][0]["target_quantity"] == 1000

@pytest.mark.asyncio
async def test_create_from_dict(async_session: AsyncSession):
    """Test creating item from dictionary."""
    item_dict = {
        "name": "7.62mm",
        "category": ItemCategory.AMMUNITION,
        "description": "Standard rifle ammunition",
        "importance": 1,
        "can_be_produced": True,
        "production_facility": ProductionLocationType.FACTORY,
        "building_targets": [
            {
                "building_type": ProductionLocationType.FACTORY,
                "target_quantity": 1000
            },
            {
                "building_type": ProductionLocationType.STORAGE_DEPOT,
                "target_quantity": 500
            }
        ]
    }
    
    item = Item.from_dict(item_dict)
    async_session.add(item)
    await async_session.commit()
    
    # Verify item was created correctly
    assert item.id is not None
    assert item.name == "7.62mm"
    assert item.category == ItemCategory.AMMUNITION
    assert item.description == "Standard rifle ammunition"
    assert item.importance == 1
    assert item.can_be_produced is True
    assert item.production_facility == ProductionLocationType.FACTORY
    assert len(item.building_targets) == 2
    assert item.get_target_quantity(ProductionLocationType.FACTORY) == 1000
    assert item.get_target_quantity(ProductionLocationType.STORAGE_DEPOT) == 500 