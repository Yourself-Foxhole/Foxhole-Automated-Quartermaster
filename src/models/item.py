"""
Item model for managing game items and their building targets.
"""

from typing import Dict, List, Optional
from sqlalchemy import Column, String, Integer, Boolean, Float, ForeignKey, Table
from sqlalchemy.orm import relationship

from src.database.database_manager import Base

# Association table for item-building relationships
item_building_targets = Table(
    'item_building_targets',
    Base.metadata,
    Column('item_id', String, ForeignKey('items.id'), primary_key=True),
    Column('building_type', String, primary_key=True),
    Column('target_quantity', Integer, nullable=False, default=0)
)

class ItemBuildingTarget(Base):
    """Model for item building target quantities."""
    __tablename__ = "item_building_targets"

    id = Column(Integer, primary_key=True)
    item_id = Column(String, ForeignKey("items.id"), nullable=False)
    building_type = Column(String, nullable=False)
    target_quantity = Column(Integer, nullable=False)

    item = relationship("Item", back_populates="building_targets")

    def __repr__(self):
        """Return a string representation of the item building target."""
        return f"<ItemBuildingTarget(item_id='{self.item_id}', building_type='{self.building_type}', target_quantity={self.target_quantity})>"

class Item(Base):
    """Model for game items."""
    __tablename__ = "items"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String)
    importance = Column(Integer, nullable=False)
    can_be_produced = Column(Boolean, default=False)
    production_facility = Column(String)

    building_targets = relationship("ItemBuildingTarget", back_populates="item", cascade="all, delete-orphan")

    def __repr__(self):
        """Return a string representation of the item."""
        return f"<Item(id='{self.id}', name='{self.name}', category='{self.category}', importance={self.importance})>"

    def get_target_quantity(self, building_type: str) -> Optional[int]:
        """Get the target quantity for a specific building type."""
        for target in self.building_targets:
            if target.building_type == building_type:
                return target.target_quantity
        return None

    def to_dict(self) -> Dict:
        """Convert item to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "importance": self.importance,
            "can_be_produced": self.can_be_produced,
            "production_facility": self.production_facility,
            "building_targets": [
                {
                    "building_type": target.building_type,
                    "target_quantity": target.target_quantity
                }
                for target in self.building_targets
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Item":
        """Create an item from dictionary data."""
        item = cls(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            description=data.get("description"),
            importance=data["importance"],
            can_be_produced=data.get("can_be_produced", False),
            production_facility=data.get("production_facility")
        )

        # Add building targets if present
        if "building_targets" in data:
            for target_data in data["building_targets"]:
                target = ItemBuildingTarget(
                    item_id=item.id,
                    building_type=target_data["building_type"],
                    target_quantity=target_data["target_quantity"]
                )
                item.building_targets.append(target)

        return item 