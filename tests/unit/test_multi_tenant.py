"""
Unit tests for multi-tenant functionality.
"""

import pytest
import uuid
from unittest.mock import Mock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from foxhole_quartermaster.models import (
    Base, User, Tenant as TenantModel, UserRole, Permission,
    TenantContext, user_tenant_membership
)
from foxhole_quartermaster.core.tenant import TenantManager, Tenant


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture
def sample_user(in_memory_db):
    """Create a sample user for testing."""
    user = User(
        discord_id="123456789",
        username="testuser",
        display_name="Test User"
    )
    in_memory_db.add(user)
    in_memory_db.commit()
    return user


@pytest.fixture
def sample_tenant_model(in_memory_db):
    """Create a sample tenant model for testing."""
    tenant_model = TenantModel(
        name="Test Regiment",
        slug="test-regiment",
        discord_guild_id="987654321",
        faction="Colonial",
        description="Test regiment for unit tests"
    )
    in_memory_db.add(tenant_model)
    in_memory_db.commit()
    return tenant_model


@pytest.fixture
def tenant_manager(in_memory_db):
    """Create a tenant manager for testing."""
    return TenantManager(in_memory_db)


class TestTenantManager:
    """Test the TenantManager class."""
    
    def test_create_tenant(self, tenant_manager, sample_user):
        """Test creating a new tenant."""
        tenant = tenant_manager.create_tenant(
            name="New Regiment",
            slug="new-regiment", 
            discord_guild_id="111222333",
            creator_user=sample_user,
            faction="Warden",
            description="A new test regiment"
        )
        
        assert tenant.name == "New Regiment"
        assert tenant.slug == "new-regiment"
        assert tenant.discord_guild_id == "111222333"
        assert tenant.faction == "Warden"
        
        # Verify creator was added as Regiment Admin
        role = tenant.get_user_role(sample_user)
        assert role == UserRole.REGIMENT_ADMIN
    
    def test_get_tenant_by_discord_guild(self, tenant_manager, sample_tenant_model):
        """Test retrieving tenant by Discord guild ID."""
        tenant = tenant_manager.get_tenant_by_discord_guild("987654321")
        assert tenant is not None
        assert tenant.slug == "test-regiment"
        
        # Test non-existent guild
        tenant = tenant_manager.get_tenant_by_discord_guild("nonexistent")
        assert tenant is None
    
    def test_get_tenant_by_slug(self, tenant_manager, sample_tenant_model):
        """Test retrieving tenant by slug."""
        tenant = tenant_manager.get_tenant_by_slug("test-regiment")
        assert tenant is not None
        assert tenant.name == "Test Regiment"
        
        # Test non-existent slug
        tenant = tenant_manager.get_tenant_by_slug("nonexistent")
        assert tenant is None
    
    def test_create_tenant_context(self, tenant_manager, sample_tenant_model, sample_user):
        """Test creating tenant context."""
        # First add user to tenant
        tenant = Tenant(sample_tenant_model, tenant_manager.db_session)
        tenant.add_member(sample_user, UserRole.LOGISTICS_MANAGER)
        
        # Create context
        context = tenant_manager.create_tenant_context("test-regiment", sample_user)
        
        assert context.tenant_id == sample_tenant_model.id
        assert context.tenant_slug == "test-regiment"
        assert context.discord_guild_id == "987654321"
        assert context.user_id == sample_user.id
        assert context.user_role == UserRole.LOGISTICS_MANAGER
        assert Permission.EDIT_SUPPLY_GRAPH in context.permissions


class TestTenant:
    """Test the Tenant class."""
    
    def test_tenant_properties(self, sample_tenant_model, in_memory_db):
        """Test tenant property access."""
        tenant = Tenant(sample_tenant_model, in_memory_db)
        
        assert tenant.id == sample_tenant_model.id
        assert tenant.name == "Test Regiment"
        assert tenant.slug == "test-regiment"
        assert tenant.discord_guild_id == "987654321"
        assert tenant.faction == "Colonial"
    
    def test_add_member(self, sample_tenant_model, sample_user, in_memory_db):
        """Test adding a member to a tenant."""
        tenant = Tenant(sample_tenant_model, in_memory_db)
        
        # Add member
        result = tenant.add_member(sample_user, UserRole.END_USER)
        assert result is True
        
        # Verify role
        role = tenant.get_user_role(sample_user)
        assert role == UserRole.END_USER
        
        # Try to add same user again
        result = tenant.add_member(sample_user, UserRole.LOGISTICS_MANAGER)
        assert result is False  # Should fail because user already exists
    
    def test_remove_member(self, sample_tenant_model, sample_user, in_memory_db):
        """Test removing a member from a tenant."""
        tenant = Tenant(sample_tenant_model, in_memory_db)
        
        # Add then remove member
        tenant.add_member(sample_user, UserRole.END_USER)
        result = tenant.remove_member(sample_user)
        assert result is True
        
        # Verify removal
        role = tenant.get_user_role(sample_user)
        assert role is None
        
        # Try to remove non-existent member
        result = tenant.remove_member(sample_user)
        assert result is False
    
    def test_update_member_role(self, sample_tenant_model, sample_user, in_memory_db):
        """Test updating a member's role."""
        tenant = Tenant(sample_tenant_model, in_memory_db)
        
        # Add member and update role
        tenant.add_member(sample_user, UserRole.END_USER)
        result = tenant.update_member_role(sample_user, UserRole.LOGISTICS_MANAGER)
        assert result is True
        
        # Verify updated role
        role = tenant.get_user_role(sample_user)
        assert role == UserRole.LOGISTICS_MANAGER
    
    def test_permission_checking(self, sample_tenant_model, sample_user, in_memory_db):
        """Test permission checking within a tenant."""
        tenant = Tenant(sample_tenant_model, in_memory_db)
        
        # Add user as end user
        tenant.add_member(sample_user, UserRole.END_USER)
        
        # Test permissions
        assert tenant.has_permission(sample_user, Permission.VIEW_TASKS)
        assert tenant.has_permission(sample_user, Permission.ACCEPT_TASKS)
        assert not tenant.has_permission(sample_user, Permission.EDIT_SUPPLY_GRAPH)
        assert not tenant.has_permission(sample_user, Permission.MANAGE_TENANT)
        
        # Update to logistics manager
        tenant.update_member_role(sample_user, UserRole.LOGISTICS_MANAGER)
        
        # Test updated permissions
        assert tenant.has_permission(sample_user, Permission.EDIT_SUPPLY_GRAPH)
        assert tenant.has_permission(sample_user, Permission.EDIT_PRODUCTION_GRAPH)
        assert not tenant.has_permission(sample_user, Permission.MANAGE_TENANT)
    
    def test_server_admin_permissions(self, sample_tenant_model, in_memory_db):
        """Test that server admins have all permissions."""
        tenant = Tenant(sample_tenant_model, in_memory_db)
        
        # Create server admin user
        admin_user = User(
            discord_id="admin123",
            username="admin",
            is_server_admin=True
        )
        in_memory_db.add(admin_user)
        in_memory_db.commit()
        
        # Server admin should have all permissions even without membership
        assert tenant.has_permission(admin_user, Permission.MANAGE_TENANT)
        assert tenant.has_permission(admin_user, Permission.EDIT_SUPPLY_GRAPH)
        assert tenant.has_permission(admin_user, Permission.VIEW_ALL_TENANTS)


class TestTenantContext:
    """Test the TenantContext class."""
    
    def test_context_permissions(self):
        """Test permission checking in tenant context."""
        context = TenantContext(
            tenant_id=uuid.uuid4(),
            tenant_slug="test",
            discord_guild_id="123",
            user_role=UserRole.LOGISTICS_MANAGER,
            permissions={Permission.EDIT_SUPPLY_GRAPH, Permission.VIEW_TASKS}
        )
        
        assert context.has_permission(Permission.EDIT_SUPPLY_GRAPH)
        assert context.has_permission(Permission.VIEW_TASKS)
        assert not context.has_permission(Permission.MANAGE_TENANT)
    
    def test_require_permission(self):
        """Test permission requirement enforcement."""
        context = TenantContext(
            tenant_id=uuid.uuid4(),
            tenant_slug="test", 
            discord_guild_id="123",
            permissions={Permission.VIEW_TASKS}
        )
        
        # Should not raise for allowed permission
        context.require_permission(Permission.VIEW_TASKS)
        
        # Should raise for disallowed permission
        with pytest.raises(PermissionError):
            context.require_permission(Permission.MANAGE_TENANT)


class TestDataIsolation:
    """Test data isolation between tenants."""
    
    def test_supply_nodes_isolated(self, in_memory_db):
        """Test that supply nodes are isolated between tenants."""
        # Create two tenants
        tenant1 = TenantModel(
            name="Tenant 1",
            slug="tenant-1",
            discord_guild_id="111"
        )
        tenant2 = TenantModel(
            name="Tenant 2", 
            slug="tenant-2",
            discord_guild_id="222"
        )
        in_memory_db.add_all([tenant1, tenant2])
        in_memory_db.commit()
        
        tenant1_obj = Tenant(tenant1, in_memory_db)
        tenant2_obj = Tenant(tenant2, in_memory_db)
        
        # Create supply nodes in each tenant
        node1 = tenant1_obj.create_supply_node("Node 1", "Location 1", "Storage")
        node2 = tenant2_obj.create_supply_node("Node 2", "Location 2", "Storage")
        
        # Verify isolation
        tenant1_nodes = tenant1_obj.get_supply_nodes()
        tenant2_nodes = tenant2_obj.get_supply_nodes()
        
        assert len(tenant1_nodes) == 1
        assert len(tenant2_nodes) == 1
        assert tenant1_nodes[0].id != tenant2_nodes[0].id
        assert tenant1_nodes[0].name == "Node 1"
        assert tenant2_nodes[0].name == "Node 2"