"""
Core multi-tenant models for the Foxhole Automated Quartermaster.

This module defines the fundamental data structures for multi-tenant operation,
including tenant isolation, user membership, and role-based access control.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, ForeignKey, 
    UniqueConstraint, Table, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func


Base = declarative_base()


class UserRole(str, Enum):
    """Standardized role hierarchy for RBAC system."""
    SERVER_ADMIN = "server_admin"      # Full control over all tenants
    REGIMENT_ADMIN = "regiment_admin"  # Full control over single tenant
    LOGISTICS_MANAGER = "logistics_manager"  # Edit supply/production graphs
    END_USER = "end_user"             # Basic operations (upload, accept tasks)


class Permission(str, Enum):
    """Granular permissions for RBAC system."""
    # Server-wide permissions
    MANAGE_ALL_TENANTS = "manage_all_tenants"
    VIEW_ALL_TENANTS = "view_all_tenants"
    MANAGE_SYSTEM_CONFIG = "manage_system_config"
    
    # Tenant-specific permissions
    MANAGE_TENANT = "manage_tenant"
    MANAGE_TENANT_USERS = "manage_tenant_users"
    MANAGE_TENANT_ROLES = "manage_tenant_roles"
    VIEW_TENANT_DATA = "view_tenant_data"
    
    # Logistics permissions
    EDIT_SUPPLY_GRAPH = "edit_supply_graph"
    EDIT_PRODUCTION_GRAPH = "edit_production_graph"
    MANAGE_INVENTORY = "manage_inventory"
    ASSIGN_TASKS = "assign_tasks"
    
    # Basic user permissions
    UPLOAD_SCREENSHOTS = "upload_screenshots"
    ACCEPT_TASKS = "accept_tasks"
    VIEW_TASKS = "view_tasks"
    MAKE_REQUESTS = "make_requests"


# Role-Permission mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.SERVER_ADMIN: {
        Permission.MANAGE_ALL_TENANTS,
        Permission.VIEW_ALL_TENANTS,
        Permission.MANAGE_SYSTEM_CONFIG,
        # Also inherits all tenant permissions for any tenant
        Permission.MANAGE_TENANT,
        Permission.MANAGE_TENANT_USERS,
        Permission.MANAGE_TENANT_ROLES,
        Permission.VIEW_TENANT_DATA,
        Permission.EDIT_SUPPLY_GRAPH,
        Permission.EDIT_PRODUCTION_GRAPH,
        Permission.MANAGE_INVENTORY,
        Permission.ASSIGN_TASKS,
        Permission.UPLOAD_SCREENSHOTS,
        Permission.ACCEPT_TASKS,
        Permission.VIEW_TASKS,
        Permission.MAKE_REQUESTS,
    },
    UserRole.REGIMENT_ADMIN: {
        Permission.MANAGE_TENANT,
        Permission.MANAGE_TENANT_USERS,
        Permission.MANAGE_TENANT_ROLES,
        Permission.VIEW_TENANT_DATA,
        Permission.EDIT_SUPPLY_GRAPH,
        Permission.EDIT_PRODUCTION_GRAPH,
        Permission.MANAGE_INVENTORY,
        Permission.ASSIGN_TASKS,
        Permission.UPLOAD_SCREENSHOTS,
        Permission.ACCEPT_TASKS,
        Permission.VIEW_TASKS,
        Permission.MAKE_REQUESTS,
    },
    UserRole.LOGISTICS_MANAGER: {
        Permission.VIEW_TENANT_DATA,
        Permission.EDIT_SUPPLY_GRAPH,
        Permission.EDIT_PRODUCTION_GRAPH,
        Permission.MANAGE_INVENTORY,
        Permission.ASSIGN_TASKS,
        Permission.UPLOAD_SCREENSHOTS,
        Permission.ACCEPT_TASKS,
        Permission.VIEW_TASKS,
        Permission.MAKE_REQUESTS,
    },
    UserRole.END_USER: {
        Permission.UPLOAD_SCREENSHOTS,
        Permission.ACCEPT_TASKS,
        Permission.VIEW_TASKS,
        Permission.MAKE_REQUESTS,
    },
}


# Association table for user-tenant membership
user_tenant_membership = Table(
    'user_tenant_membership',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('tenant_id', UUID(as_uuid=True), ForeignKey('tenants.id'), primary_key=True),
    Column('role', SQLEnum(UserRole), nullable=False),
    Column('joined_at', DateTime(timezone=True), server_default=func.now()),
    Column('is_active', Boolean, default=True),
    UniqueConstraint('user_id', 'tenant_id', name='unique_user_tenant'),
)


class User(Base):
    """User account that can belong to multiple tenants with different roles."""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discord_id = Column(String(32), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    display_name = Column(String(100))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # Server-wide admin status (overrides tenant permissions)
    is_server_admin = Column(Boolean, default=False)
    
    # Many-to-many relationship with tenants
    tenant_memberships = relationship(
        "Tenant",
        secondary=user_tenant_membership,
        back_populates="members"
    )
    
    def has_permission(self, permission: Permission, tenant_id: Optional[uuid.UUID] = None) -> bool:
        """Check if user has specific permission, optionally within a tenant context."""
        # Server admins have all permissions
        if self.is_server_admin:
            return True
            
        # For tenant-specific permissions, check role in that tenant
        if tenant_id:
            membership = self.get_tenant_membership(tenant_id)
            if membership:
                role = membership['role']
                return permission in ROLE_PERMISSIONS.get(role, set())
        
        return False
    
    def get_tenant_membership(self, tenant_id: uuid.UUID) -> Optional[Dict]:
        """Get user's membership details for a specific tenant."""
        # This would be implemented with proper SQLAlchemy query
        # For now, returning None as placeholder
        return None
    
    def get_tenant_role(self, tenant_id: uuid.UUID) -> Optional[UserRole]:
        """Get user's role in a specific tenant."""
        membership = self.get_tenant_membership(tenant_id)
        return membership['role'] if membership else None


class Tenant(Base):
    """
    A tenant represents a regiment or organization using the bot.
    All data and operations are scoped to a tenant for complete isolation.
    """
    __tablename__ = 'tenants'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)
    
    # Discord server/guild this tenant is associated with
    discord_guild_id = Column(String(32), unique=True, nullable=False, index=True)
    
    # Foxhole game faction (Colonial/Warden)
    faction = Column(String(20))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Configuration specific to this tenant
    config = Column(Text)  # JSON blob for tenant-specific settings
    
    # Many-to-many relationship with users
    members = relationship(
        "User",
        secondary=user_tenant_membership,
        back_populates="tenant_memberships"
    )
    
    # One-to-many relationships with tenant-scoped data
    supply_nodes = relationship("SupplyNode", back_populates="tenant")
    production_nodes = relationship("ProductionNode", back_populates="tenant")
    logistics_tasks = relationship("LogisticsTask", back_populates="tenant")
    
    def add_member(self, user: User, role: UserRole) -> bool:
        """Add a user to this tenant with specified role."""
        # Implementation would use SQLAlchemy session
        # This is a placeholder for the interface
        return True
    
    def remove_member(self, user: User) -> bool:
        """Remove a user from this tenant."""
        # Implementation would use SQLAlchemy session
        return True
    
    def update_member_role(self, user: User, new_role: UserRole) -> bool:
        """Update a user's role in this tenant."""
        # Implementation would use SQLAlchemy session
        return True
    
    def get_members_by_role(self, role: UserRole) -> List[User]:
        """Get all users with a specific role in this tenant."""
        # Implementation would use SQLAlchemy query
        return []


# Tenant-scoped data models
class SupplyNode(Base):
    """Supply locations and inventory, scoped to tenant."""
    __tablename__ = 'supply_nodes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    location = Column(String(100))  # In-game location
    node_type = Column(String(50))  # Storage, Depot, etc.
    
    # Current inventory state (JSON blob)
    inventory = Column(Text)
    # Desired inventory state (JSON blob)
    desired_state = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    tenant = relationship("Tenant", back_populates="supply_nodes")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='unique_tenant_supply_node'),
    )


class ProductionNode(Base):
    """Production facilities and capabilities, scoped to tenant."""
    __tablename__ = 'production_nodes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    location = Column(String(100))
    facility_type = Column(String(50))  # Factory, Mass Production, etc.
    
    # Production queue and capabilities (JSON blob)
    production_queue = Column(Text)
    capabilities = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    tenant = relationship("Tenant", back_populates="production_nodes")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='unique_tenant_production_node'),
    )


class LogisticsTask(Base):
    """Individual logistics tasks, scoped to tenant."""
    __tablename__ = 'logistics_tasks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    
    title = Column(String(200), nullable=False)
    description = Column(Text)
    task_type = Column(String(50))  # Transport, Production, etc.
    
    # Task details (JSON blob)
    task_data = Column(Text)
    
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    status = Column(String(50), default='pending')  # pending, in_progress, completed, cancelled
    priority = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    due_date = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    tenant = relationship("Tenant", back_populates="logistics_tasks")
    assignee = relationship("User", foreign_keys=[assigned_to])
    creator = relationship("User", foreign_keys=[created_by])


@dataclass
class TenantContext:
    """
    Runtime context for tenant operations.
    Used to scope all operations to a specific tenant.
    """
    tenant_id: uuid.UUID
    tenant_slug: str
    discord_guild_id: str
    user_id: Optional[uuid.UUID] = None
    user_role: Optional[UserRole] = None
    permissions: Set[Permission] = field(default_factory=set)
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if the current context has a specific permission."""
        return permission in self.permissions
    
    def require_permission(self, permission: Permission) -> None:
        """Raise exception if the current context lacks a specific permission."""
        if not self.has_permission(permission):
            raise PermissionError(
                f"Permission '{permission.value}' required for this operation in tenant '{self.tenant_slug}'"
            )


class TenantPermissionError(Exception):
    """Raised when a user lacks required permissions for a tenant operation."""
    pass


class TenantNotFoundError(Exception):
    """Raised when a referenced tenant cannot be found."""
    pass


class UserNotMemberError(Exception):
    """Raised when a user is not a member of the specified tenant."""
    pass