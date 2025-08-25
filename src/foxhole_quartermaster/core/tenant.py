"""
Core tenant management system for multi-tenant Discord bot.

This module provides the central tenant abstraction that encapsulates all state
and logic for a single regiment, ensuring complete data isolation between tenants.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, List, Optional, Set, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models import (
    Tenant as TenantModel, User, TenantContext, UserRole, Permission,
    SupplyNode, ProductionNode, LogisticsTask,
    TenantNotFoundError, UserNotMemberError, TenantPermissionError,
    ROLE_PERMISSIONS
)


class TenantManager:
    """
    Central manager for all tenant operations.
    Ensures proper isolation and permission enforcement.
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self._tenant_cache: Dict[str, 'Tenant'] = {}
    
    def get_tenant_by_discord_guild(self, guild_id: str) -> Optional['Tenant']:
        """Get tenant associated with a Discord guild/server."""
        tenant_model = self.db_session.query(TenantModel).filter(
            TenantModel.discord_guild_id == guild_id,
            TenantModel.is_active == True
        ).first()
        
        if not tenant_model:
            return None
            
        return Tenant(tenant_model, self.db_session)
    
    def get_tenant_by_slug(self, slug: str) -> Optional['Tenant']:
        """Get tenant by its unique slug identifier."""
        if slug in self._tenant_cache:
            return self._tenant_cache[slug]
            
        tenant_model = self.db_session.query(TenantModel).filter(
            TenantModel.slug == slug,
            TenantModel.is_active == True
        ).first()
        
        if not tenant_model:
            return None
            
        tenant = Tenant(tenant_model, self.db_session)
        self._tenant_cache[slug] = tenant
        return tenant
    
    def create_tenant(
        self, 
        name: str, 
        slug: str, 
        discord_guild_id: str,
        creator_user: User,
        faction: Optional[str] = None,
        description: Optional[str] = None
    ) -> 'Tenant':
        """Create a new tenant with the creator as Regiment Admin."""
        # Check if tenant already exists
        existing = self.db_session.query(TenantModel).filter(
            (TenantModel.slug == slug) | (TenantModel.discord_guild_id == discord_guild_id)
        ).first()
        
        if existing:
            raise ValueError(f"Tenant with slug '{slug}' or guild '{discord_guild_id}' already exists")
        
        tenant_model = TenantModel(
            name=name,
            slug=slug,
            discord_guild_id=discord_guild_id,
            faction=faction,
            description=description
        )
        
        self.db_session.add(tenant_model)
        self.db_session.flush()  # Get the ID
        
        # Add creator as Regiment Admin
        tenant = Tenant(tenant_model, self.db_session)
        tenant.add_member(creator_user, UserRole.REGIMENT_ADMIN)
        
        self.db_session.commit()
        return tenant
    
    def list_user_tenants(self, user: User) -> List['Tenant']:
        """List all tenants a user belongs to."""
        tenant_models = self.db_session.query(TenantModel).join(
            TenantModel.members
        ).filter(
            User.id == user.id,
            TenantModel.is_active == True
        ).all()
        
        return [Tenant(tm, self.db_session) for tm in tenant_models]
    
    def create_tenant_context(
        self, 
        tenant_slug: str, 
        user: Optional[User] = None
    ) -> TenantContext:
        """Create a tenant context for scoped operations."""
        tenant = self.get_tenant_by_slug(tenant_slug)
        if not tenant:
            raise TenantNotFoundError(f"Tenant '{tenant_slug}' not found")
        
        context = TenantContext(
            tenant_id=tenant.model.id,
            tenant_slug=tenant_slug,
            discord_guild_id=tenant.model.discord_guild_id
        )
        
        if user:
            # Check if user is member and get their role/permissions
            role = tenant.get_user_role(user)
            if role:
                context.user_id = user.id
                context.user_role = role
                context.permissions = ROLE_PERMISSIONS.get(role, set())
            elif user.is_server_admin:
                # Server admins can access any tenant
                context.user_id = user.id
                context.user_role = UserRole.SERVER_ADMIN
                context.permissions = ROLE_PERMISSIONS[UserRole.SERVER_ADMIN]
        
        return context


class Tenant:
    """
    Tenant abstraction that encapsulates all state and logic for a single regiment.
    Provides isolated operations and ensures data cannot leak between tenants.
    """
    
    def __init__(self, model: TenantModel, db_session: Session):
        self.model = model
        self.db_session = db_session
        self._config_cache: Optional[Dict[str, Any]] = None
    
    @property
    def id(self) -> uuid.UUID:
        return self.model.id
    
    @property
    def name(self) -> str:
        return self.model.name
    
    @property
    def slug(self) -> str:
        return self.model.slug
    
    @property
    def discord_guild_id(self) -> str:
        return self.model.discord_guild_id
    
    @property
    def faction(self) -> Optional[str]:
        return self.model.faction
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get tenant-specific configuration."""
        if self._config_cache is None:
            if self.model.config:
                self._config_cache = json.loads(self.model.config)
            else:
                self._config_cache = {}
        return self._config_cache
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """Update tenant configuration."""
        self.model.config = json.dumps(config)
        self._config_cache = config
        self.db_session.commit()
    
    # Member management
    def add_member(self, user: User, role: UserRole) -> bool:
        """Add a user to this tenant with specified role."""
        from sqlalchemy import text
        
        # Check if user is already a member
        existing = self.db_session.execute(
            text("SELECT 1 FROM user_tenant_membership WHERE user_id = :user_id AND tenant_id = :tenant_id"),
            {"user_id": str(user.id), "tenant_id": str(self.id)}
        ).first()
        
        if existing:
            return False
        
        # Add membership
        self.db_session.execute(
            text("""INSERT INTO user_tenant_membership (user_id, tenant_id, role, is_active) 
               VALUES (:user_id, :tenant_id, :role, true)"""),
            {"user_id": str(user.id), "tenant_id": str(self.id), "role": role.value}
        )
        self.db_session.commit()
        return True
    
    def remove_member(self, user: User) -> bool:
        """Remove a user from this tenant."""
        from sqlalchemy import text
        
        result = self.db_session.execute(
            text("DELETE FROM user_tenant_membership WHERE user_id = :user_id AND tenant_id = :tenant_id"),
            {"user_id": str(user.id), "tenant_id": str(self.id)}
        )
        self.db_session.commit()
        return result.rowcount > 0
    
    def update_member_role(self, user: User, new_role: UserRole) -> bool:
        """Update a user's role in this tenant."""
        from sqlalchemy import text
        
        result = self.db_session.execute(
            text("""UPDATE user_tenant_membership 
               SET role = :role 
               WHERE user_id = :user_id AND tenant_id = :tenant_id"""),
            {"role": new_role.value, "user_id": str(user.id), "tenant_id": str(self.id)}
        )
        self.db_session.commit()
        return result.rowcount > 0
    
    def get_user_role(self, user: User) -> Optional[UserRole]:
        """Get a user's role in this tenant."""
        from sqlalchemy import text
        
        result = self.db_session.execute(
            text("""SELECT role FROM user_tenant_membership 
               WHERE user_id = :user_id AND tenant_id = :tenant_id AND is_active = true"""),
            {"user_id": str(user.id), "tenant_id": str(self.id)}
        ).first()
        
        return UserRole(result[0]) if result else None
    
    def get_members_by_role(self, role: UserRole) -> List[User]:
        """Get all users with a specific role in this tenant."""
        users = self.db_session.query(User).join(
            "user_tenant_membership"
        ).filter(
            and_(
                User.tenant_memberships.any(TenantModel.id == self.id),
                # Additional filter for role would be added here
            )
        ).all()
        return users
    
    def list_all_members(self) -> List[Dict[str, Any]]:
        """List all members with their roles."""
        from sqlalchemy import text
        
        results = self.db_session.execute(
            text("""SELECT u.id, u.username, u.display_name, utm.role, utm.joined_at
               FROM users u 
               JOIN user_tenant_membership utm ON u.id = utm.user_id
               WHERE utm.tenant_id = :tenant_id AND utm.is_active = true
               ORDER BY utm.joined_at"""),
            {"tenant_id": str(self.id)}
        ).fetchall()
        
        return [
            {
                "user_id": row[0],
                "username": row[1],
                "display_name": row[2],
                "role": UserRole(row[3]),
                "joined_at": row[4]
            }
            for row in results
        ]
    
    # Supply chain operations (tenant-scoped)
    def get_supply_nodes(self) -> List[SupplyNode]:
        """Get all supply nodes for this tenant."""
        return self.db_session.query(SupplyNode).filter(
            SupplyNode.tenant_id == self.id,
            SupplyNode.is_active == True
        ).all()
    
    def create_supply_node(self, name: str, location: str, node_type: str) -> SupplyNode:
        """Create a new supply node for this tenant."""
        node = SupplyNode(
            tenant_id=self.id,
            name=name,
            location=location,
            node_type=node_type,
            inventory="{}",
            desired_state="{}"
        )
        self.db_session.add(node)
        self.db_session.commit()
        return node
    
    def get_production_nodes(self) -> List[ProductionNode]:
        """Get all production nodes for this tenant."""
        return self.db_session.query(ProductionNode).filter(
            ProductionNode.tenant_id == self.id,
            ProductionNode.is_active == True
        ).all()
    
    def create_production_node(self, name: str, location: str, facility_type: str) -> ProductionNode:
        """Create a new production node for this tenant."""
        node = ProductionNode(
            tenant_id=self.id,
            name=name,
            location=location,
            facility_type=facility_type,
            production_queue="[]",
            capabilities="{}"
        )
        self.db_session.add(node)
        self.db_session.commit()
        return node
    
    # Task management (tenant-scoped)
    def get_logistics_tasks(self, status: Optional[str] = None) -> List[LogisticsTask]:
        """Get logistics tasks for this tenant, optionally filtered by status."""
        query = self.db_session.query(LogisticsTask).filter(
            LogisticsTask.tenant_id == self.id
        )
        if status:
            query = query.filter(LogisticsTask.status == status)
        return query.order_by(LogisticsTask.created_at.desc()).all()
    
    def create_logistics_task(
        self, 
        title: str, 
        description: str,
        task_type: str,
        creator: User,
        task_data: Optional[Dict[str, Any]] = None,
        assignee: Optional[User] = None
    ) -> LogisticsTask:
        """Create a new logistics task for this tenant."""
        task = LogisticsTask(
            tenant_id=self.id,
            title=title,
            description=description,
            task_type=task_type,
            created_by=creator.id,
            assigned_to=assignee.id if assignee else None,
            task_data=json.dumps(task_data or {}),
            status="pending"
        )
        self.db_session.add(task)
        self.db_session.commit()
        return task
    
    # Permission checking
    def require_permission(self, user: User, permission: Permission) -> None:
        """
        Verify that a user has the required permission in this tenant.
        Raises TenantPermissionError if permission is denied.
        """
        if user.is_server_admin:
            return  # Server admins have all permissions
        
        role = self.get_user_role(user)
        if not role:
            raise UserNotMemberError(f"User {user.username} is not a member of tenant {self.slug}")
        
        if permission not in ROLE_PERMISSIONS.get(role, set()):
            raise TenantPermissionError(
                f"User {user.username} lacks permission {permission.value} in tenant {self.slug}"
            )
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if a user has a specific permission in this tenant."""
        try:
            self.require_permission(user, permission)
            return True
        except (UserNotMemberError, TenantPermissionError):
            return False
    
    def __str__(self) -> str:
        return f"Tenant(slug='{self.slug}', name='{self.name}')"
    
    def __repr__(self) -> str:
        return f"Tenant(id={self.id}, slug='{self.slug}', guild_id='{self.discord_guild_id}')"