"""
Item model for the Foxhole Logistics Network.
"""

from typing import Dict, List, Optional
from sqlalchemy import Column, String, Integer, Boolean, Float, ForeignKey, Table, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

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
    item_id = Column(String, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    building_type = Column(String, nullable=False)
    target_quantity = Column(Integer, nullable=False)

    item = relationship("Item", back_populates="building_targets")

    def __repr__(self):
        """Return a string representation of the item building target."""
        return f"<ItemBuildingTarget(item_id={self.item_id}, building_type={self.building_type}, target_quantity={self.target_quantity})>"

class ItemProductionInput(Base):
    """Model for item production inputs."""
    
    __tablename__ = "item_production_inputs"
    
    id = Column(Integer, primary_key=True)
    item_id = Column(String, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    input_item_id = Column(String, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    # Relationships
    item = relationship("Item", foreign_keys=[item_id], back_populates="production_inputs")
    input_item = relationship("Item", foreign_keys=[input_item_id])
    
    def __repr__(self):
        return f"<ItemProductionInput(item_id={self.item_id}, input_item_id={self.input_item_id}, quantity={self.quantity})>"

class Item(Base):
    """Model for game items."""
    __tablename__ = "items"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)
    description = Column(String)
    importance = Column(Integer, default=3)
    can_be_produced = Column(Boolean, default=False)
    production_facility = Column(String)
    stack_size = Column(Integer)
    production_output = Column(Integer, default=1)

    building_targets = relationship("ItemBuildingTarget", back_populates="item", cascade="all, delete-orphan")
    production_inputs = relationship("ItemProductionInput", back_populates="item", cascade="all, delete-orphan")

    def __repr__(self):
        """Return a string representation of the item."""
        return f"<Item(id={self.id}, name={self.name}, category={self.category})>"

    def get_target_quantity(self, building_type: str) -> int:
        """Get the target quantity for a specific building type."""
        for target in self.building_targets:
            if target.building_type == building_type:
                return target.target_quantity
        return 0

    def to_dict(self) -> dict:
        """Convert item to dictionary format."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "importance": self.importance,
            "can_be_produced": self.can_be_produced,
            "production_facility": self.production_facility,
            "stack_size": self.stack_size,
            "production_output": self.production_output,
            "building_targets": [
                {
                    "building_type": target.building_type,
                    "target_quantity": target.target_quantity
                }
                for target in self.building_targets
            ],
            "production_inputs": [
                {
                    "input_item_id": input.input_item_id,
                    "quantity": input.quantity
                }
                for input in self.production_inputs
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        """Create an item from dictionary data."""
        item = cls(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            description=data.get("description"),
            importance=data.get("importance", 3),
            can_be_produced=data.get("can_be_produced", False),
            production_facility=data.get("production_facility"),
            stack_size=data.get("stack_size"),
            production_output=data.get("production_output", 1)
        )
        
        # Add building targets
        for target_data in data.get("building_targets", []):
            target = ItemBuildingTarget(
                item_id=item.id,
                building_type=target_data["building_type"],
                target_quantity=target_data["target_quantity"]
            )
            item.building_targets.append(target)
        
        # Add production inputs
        for input_data in data.get("production_inputs", []):
            input_item = ItemProductionInput(
                item_id=item.id,
                input_item_id=input_data["input_item_id"],
                quantity=input_data["quantity"]
            )
            item.production_inputs.append(input_item)
        
        return item 