"""
Database models for the Foxhole Logistics Bot.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean, Float, Enum as SQLEnum, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# Enumerations
class LocationType(str, Enum):
    """Types of locations in the game."""
    FORWARD_BASE = "forward_base"
    FRONTLINE_HUB = "frontline_hub"
    BACKLINE_HUB = "backline_hub"
    REFINERY = "refinery"
    FACTORY = "factory"
    MPF = "mpf"
    FACILITY = "facility"
    RESOURCE_FIELD = "resource_field"


class TaskType(str, Enum):
    """Types of logistics tasks."""
    RAW = "raw"
    REFINE_IN_PROGRESS = "refine_in_progress"
    REFINE_WAITING_PICKUP = "refine_waiting_pickup"
    MANUFACTURE_PENDING = "manufacture_pending"
    MANUFACTURE_IN_PROGRESS = "manufacture_in_progress"
    MANUFACTURE_COMPLETE = "manufacture_complete"
    FACILITY_PENDING = "facility_pending"
    FACILITY_COMPLETE = "facility_complete"
    TRANSPORT_MIDLINE_PENDING = "transport_midline_pending"
    TRANSPORT_FRONTLINE_STAGED = "transport_frontline_staged"
    FRONTLINE_DELIVERY = "frontline_delivery"


class TaskStatus(str, Enum):
    """Status states for tasks."""
    UNCLAIMED = "unclaimed"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class ProductionLocationType(str, Enum):
    """Types of production locations."""
    FACTORY = "factory"
    MPF = "mpf"
    FACILITY = "facility"
    REFINERY = "refinery"


class UrgencyLevel(str, Enum):
    """Urgency levels for tasks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TransportLoadType(str, Enum):
    """Types of transport loads."""
    FTL = "ftl"  # Full Truck Load (15 crates)
    FCL = "fcl"  # Full Container Load (60 crates)
    LIQUID = "liquid"  # Liquid Container (100 cans)
    SHIPPABLE = "shippable"  # Pre-packaged shippable (3 vehicles)


class ItemCategory(str, Enum):
    """Categories of items in the game."""
    WEAPON = "weapon"
    AMMUNITION = "ammunition"
    VEHICLE = "vehicle"
    MEDICAL = "medical"
    UNIFORM = "uniform"
    BUILDING = "building"
    RAW_RESOURCE = "raw_resource"
    REFINED_RESOURCE = "refined_resource"
    TOOL = "tool"
    SUPPLY = "supply"
    OTHER = "other"


# Discord-related models
class Regiment(Base):
    """
    Represents a Discord regiment (server) in the database.
    """
    __tablename__ = "regiments"

    id = Column(Integer, primary_key=True)
    regiment_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    channels = relationship("Channel", back_populates="regiment", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="regiment", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="regiment", cascade="all, delete-orphan")


class Channel(Base):
    """
    Represents a Discord channel in the database.
    """
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    regiment_id = Column(Integer, ForeignKey("regiments.id"), nullable=False)
    channel_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    channel_type = Column(String, nullable=False)  # text, voice, category, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    regiment = relationship("Regiment", back_populates="channels")


class Role(Base):
    """
    Represents a Discord role in the database.
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    regiment_id = Column(Integer, ForeignKey("regiments.id"), nullable=False)
    role_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    color = Column(String, nullable=True)
    permissions = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    regiment = relationship("Regiment", back_populates="roles")


class User(Base):
    """
    Represents a Discord user in the database.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    discriminator = Column(String, nullable=True)
    avatar = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    notification_preferences = Column(JSON, nullable=True)
    current_pending_tasks = Column(Integer, default=0)
    last_active = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    claimed_tasks = relationship("Task", back_populates="claimed_by_user")
    reported_inventories = relationship("Inventory", back_populates="reported_by_user")
    task_history_entries = relationship("TaskHistory", back_populates="changed_by_user")


class UserRole(Base):
    """
    Many-to-many relationship between Users and Roles.
    """
    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role")


class LogEntry(Base):
    """
    Represents a log entry in the database.
    """
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True)
    regiment_id = Column(Integer, ForeignKey("regiments.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)  # create, update, delete, etc.
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    regiment = relationship("Regiment")
    channel = relationship("Channel")
    user = relationship("User")


# Game-related models
class Location(Base):
    """
    Represents a location in the game where items can be stored or produced.
    """
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    regiment_id = Column(Integer, ForeignKey("regiments.id"), nullable=False)
    name = Column(String, nullable=False)
    location_type = Column(SQLEnum(LocationType), nullable=False)
    coordinates = Column(String, nullable=True)
    managed_by_role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    regiment = relationship("Regiment", back_populates="locations")
    managed_by_role = relationship("Role")
    inventories = relationship("Inventory", back_populates="location", cascade="all, delete-orphan")
    location_buffers = relationship("LocationBuffer", back_populates="location", cascade="all, delete-orphan")
    source_tasks = relationship("Task", foreign_keys="Task.source_location_id", back_populates="source_location")
    target_tasks = relationship("Task", foreign_keys="Task.target_location_id", back_populates="target_location")
    source_locations = relationship("LocationSource", foreign_keys="LocationSource.source_location_id", back_populates="source_location")
    target_locations = relationship("LocationSource", foreign_keys="LocationSource.location_id", back_populates="target_location")


class LocationSource(Base):
    """
    Many-to-many relationship showing which locations supply other locations.
    """
    __tablename__ = "location_sources"

    location_id = Column(Integer, ForeignKey("locations.id"), primary_key=True)
    source_location_id = Column(Integer, ForeignKey("locations.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    target_location = relationship("Location", foreign_keys=[location_id], back_populates="target_locations")
    source_location = relationship("Location", foreign_keys=[source_location_id], back_populates="source_locations")


class ItemBuildingTarget(Base):
    """
    Represents the target quantity of an item for a specific building type.
    """
    __tablename__ = "item_building_targets"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"))
    building_type = Column(String)
    target_quantity = Column(Integer)

    # Relationship
    item = relationship("Item", back_populates="building_targets")

    def __repr__(self):
        return f"<ItemBuildingTarget(item_id={self.item_id}, building_type={self.building_type}, target_quantity={self.target_quantity})>"


class ItemProductionInput(Base):
    """Represents the production inputs required for an item."""
    __tablename__ = "item_production_inputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    input_item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    quantity: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    item: Mapped["Item"] = relationship("Item", foreign_keys=[item_id], back_populates="production_inputs")
    input_item: Mapped["Item"] = relationship("Item", foreign_keys=[input_item_id])

    def __repr__(self) -> str:
        return f"<ItemProductionInput(id={self.id}, item_id={self.item_id}, input_item_id={self.input_item_id}, quantity={self.quantity})>"


class Item(Base):
    """Represents a game item."""
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    category: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    importance: Mapped[int] = mapped_column(default=1)
    can_be_produced: Mapped[bool] = mapped_column(default=False)
    production_facility: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    building_targets: Mapped[List["ItemBuildingTarget"]] = relationship("ItemBuildingTarget", back_populates="item", cascade="all, delete-orphan")
    production_inputs: Mapped[List["ItemProductionInput"]] = relationship("ItemProductionInput", foreign_keys="[ItemProductionInput.item_id]", back_populates="item")
    inventories = relationship("Inventory", back_populates="item")
    location_buffers = relationship("LocationBuffer", back_populates="item")
    tasks = relationship("Task", back_populates="item")
    recipes = relationship("Recipe", back_populates="output_item")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient_item")

    def get_target_quantity(self, building_type: str) -> Optional[int]:
        """Get the target quantity for a specific building type."""
        target = next((t for t in self.building_targets if t.building_type == building_type), None)
        return target.target_quantity if target else None

    def to_dict(self) -> dict:
        """Convert the item to a dictionary."""
        return {
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
    def from_dict(cls, data: dict) -> "Item":
        """Create an item from a dictionary."""
        building_targets_data = data.pop("building_targets", [])
        item = cls(**data)
        
        for target_data in building_targets_data:
            target = ItemBuildingTarget(
                building_type=target_data["building_type"],
                target_quantity=target_data["target_quantity"]
            )
            item.building_targets.append(target)
        
        return item

    def __repr__(self) -> str:
        return f"<Item(id={self.id}, name='{self.name}', category='{self.category}')>"


class Recipe(Base):
    """
    Defines how items are produced and what input materials are required.
    """
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    output_item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    output_quantity = Column(Integer, nullable=False)
    production_location_type = Column(SQLEnum(ProductionLocationType), nullable=False)
    production_time = Column(Integer, nullable=False)  # Time in minutes to produce
    mpf_discount_eligible = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    output_item = relationship("Item", back_populates="recipes")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")


class RecipeIngredient(Base):
    """
    Many-to-many relationship between Recipes and Items that are used as inputs.
    """
    __tablename__ = "recipe_ingredients"

    recipe_id = Column(Integer, ForeignKey("recipes.id"), primary_key=True)
    ingredient_item_id = Column(Integer, ForeignKey("items.id"), primary_key=True)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient_item = relationship("Item", back_populates="recipe_ingredients")


class Inventory(Base):
    """
    Tracks the last reported inventory level of an item at a specific location.
    """
    __tablename__ = "inventories"

    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    last_updated = Column(DateTime, nullable=False)
    reported_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('location_id', 'item_id', name='uix_inventory_location_item'),
    )

    # Relationships
    location = relationship("Location", back_populates="inventories")
    item = relationship("Item", back_populates="inventories")
    reported_by_user = relationship("User", back_populates="reported_inventories")


class Task(Base):
    """
    The central entity that represents a specific logistics task to be completed.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(SQLEnum(TaskStatus), nullable=False)
    priority_score = Column(Integer, nullable=False)
    source_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    target_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    claimed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    linked_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    production_location_type = Column(SQLEnum(ProductionLocationType), nullable=True)
    estimated_completion_time = Column(DateTime, nullable=True)
    claim_timeout = Column(DateTime, nullable=True)
    pending_timeout = Column(DateTime, nullable=True)
    urgency = Column(SQLEnum(UrgencyLevel), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    item = relationship("Item", back_populates="tasks")
    source_location = relationship("Location", foreign_keys=[source_location_id], back_populates="source_tasks")
    target_location = relationship("Location", foreign_keys=[target_location_id], back_populates="target_tasks")
    claimed_by_user = relationship("User", back_populates="claimed_tasks")
    parent_task = relationship("Task", remote_side=[id], backref="child_tasks")
    history = relationship("TaskHistory", back_populates="task", cascade="all, delete-orphan")


class LocationBuffer(Base):
    """
    Defines the desired buffer levels for items at specific locations.
    """
    __tablename__ = "location_buffers"

    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    target_quantity = Column(Integer, nullable=False)
    critical_threshold_percent = Column(Integer, nullable=False)
    alert_role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    default_production_location = Column(SQLEnum(ProductionLocationType), nullable=True)
    default_transport_load_type = Column(SQLEnum(TransportLoadType), nullable=True)
    priority_score = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('location_id', 'item_id', name='uix_location_buffer_location_item'),
    )

    # Relationships
    location = relationship("Location", back_populates="location_buffers")
    item = relationship("Item", back_populates="location_buffers")
    alert_role = relationship("Role")


class TaskHistory(Base):
    """
    Audit log of task state changes.
    """
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    previous_status = Column(SQLEnum(TaskStatus), nullable=False)
    new_status = Column(SQLEnum(TaskStatus), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Relationships
    task = relationship("Task", back_populates="history")
    changed_by_user = relationship("User", back_populates="task_history_entries")


class Config(Base):
    """
    Global configuration settings for the bot.
    """
    __tablename__ = "configs"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 