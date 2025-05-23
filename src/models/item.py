"""
Models for managing game items and their building target quantities.
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from src.models.enums import ItemCategory, ProductionLocationType

Base = declarative_base()

class ItemBuildingTarget(Base):
    """Represents target quantities for items at different building types."""
    __tablename__ = 'item_building_targets'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id', ondelete='CASCADE'))
    building_type = Column(Enum(ProductionLocationType), nullable=False)
    target_quantity = Column(Integer, nullable=False)

    # Relationship back to the item
    item = relationship("Item", back_populates="building_targets")

    def __repr__(self):
        return f"<ItemBuildingTarget(item_id={self.item_id}, building_type={self.building_type}, target_quantity={self.target_quantity})>"

class Item(Base):
    """Represents an item in the game."""
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(Enum(ItemCategory), nullable=False)
    description = Column(String)
    importance = Column(Integer, default=0)
    can_be_produced = Column(Boolean, default=True)
    production_facility = Column(Enum(ProductionLocationType), nullable=True)

    # Relationship to building targets
    building_targets = relationship("ItemBuildingTarget", back_populates="item", cascade="all, delete-orphan")

    def get_target_quantity(self, building_type: ProductionLocationType) -> int:
        """Get the target quantity for this item at a specific building type."""
        for target in self.building_targets:
            if target.building_type == building_type:
                return target.target_quantity
        return 0

    def to_dict(self) -> dict:
        """Convert the item to a dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category.name,
            'description': self.description,
            'importance': self.importance,
            'can_be_produced': self.can_be_produced,
            'production_facility': self.production_facility.name if self.production_facility else None,
            'building_targets': [
                {
                    'building_type': target.building_type.name,
                    'target_quantity': target.target_quantity
                }
                for target in self.building_targets
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Item':
        """Create an Item instance from a dictionary."""
        building_targets_data = data.pop('building_targets', [])
        
        # Convert string enums to actual enum values
        if 'category' in data:
            data['category'] = ItemCategory[data['category']]
        if 'production_facility' in data and data['production_facility']:
            data['production_facility'] = ProductionLocationType[data['production_facility']]

        item = cls(**data)
        
        # Create building targets
        for target_data in building_targets_data:
            target = ItemBuildingTarget(
                building_type=ProductionLocationType[target_data['building_type']],
                target_quantity=target_data['target_quantity']
            )
            item.building_targets.append(target)
        
        return item

    def __repr__(self):
        return f"<Item(name='{self.name}', category={self.category})>" 