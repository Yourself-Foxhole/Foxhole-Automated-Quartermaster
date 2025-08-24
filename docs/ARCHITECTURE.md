# Multi-Tenant Architecture Documentation

## Overview

The Foxhole Automated Quartermaster implements a comprehensive multi-tenant architecture that allows multiple regiments (Discord servers) to use the same bot instance while maintaining complete data isolation and security.

## Core Components

### 1. Tenant Abstraction

**Tenant Class** (`src/foxhole_quartermaster/core/tenant.py`)
- Encapsulates all state and logic for a single regiment
- Contains: supply graph, production graph, user roster, active tasks, inventory state, desired state, and configuration
- Provides isolated operations ensuring no data leakage between tenants

**TenantManager Class**
- Central manager for all tenant operations
- Handles tenant creation, lookup, and context management
- Maintains tenant cache for performance

### 2. Role-Based Access Control (RBAC)

**Role Hierarchy:**
- **Server Admin**: Full control over all tenants and system-wide configuration
- **Regiment Admin**: Full control over single tenant (regiment)
- **Logistics Manager**: Can edit supply/production graphs for their tenant
- **End User**: Can upload screenshots, accept tasks, perform basic requests

**Permission System:**
- Granular permissions mapped to roles
- Server admins can access any tenant
- All operations require appropriate permissions
- Permission checks enforced at the tenant context level

### 3. Data Isolation

**Database Design:**
- All tenant-scoped tables include `tenant_id` foreign key
- User-tenant membership tracked separately with roles
- No cross-tenant data sharing except for server admin operations
- Tenant-specific configuration stored as JSON

**Query Scoping:**
- All data access filtered by tenant context
- Tenant operations wrapped in permission checks
- Explicit tenant context required for all operations

### 4. Discord Integration

**Command Routing:**
- Commands automatically determine tenant from Discord guild
- Tenant context created for each command invocation
- Permission enforcement at command level using decorators

**Guild Management:**
- Each Discord server maps to one tenant
- Automatic tenant detection from guild ID
- Setup commands for new regiment registration

## Security Features

### Data Isolation
- No tenant can access another tenant's data
- Server admin access logged and restricted to operational purposes
- Database queries automatically scoped by tenant

### Permission Enforcement
- All commands check user permissions before execution
- Role-based access control prevents unauthorized operations
- Tenant membership required for all tenant-specific commands

### Audit Trail
- All operations logged with user and tenant context
- Database timestamps on all data modifications
- Permission changes tracked per tenant

## Extending the System

### Adding New Roles
1. Add role to `UserRole` enum in `models/__init__.py`
2. Define permissions in `ROLE_PERMISSIONS` mapping
3. Update command decorators as needed

### Adding New Permissions
1. Add permission to `Permission` enum
2. Map to appropriate roles in `ROLE_PERMISSIONS`
3. Use in command decorators: `@bot.require_permission(Permission.NEW_PERMISSION)`

### Adding New Commands
```python
@tenant_command(name='new_command')
async def new_command(
    self, 
    ctx: commands.Context,
    tenant_context: Optional[TenantContext] = None
):
    if not tenant_context:
        return
    
    tenant_context.require_permission(Permission.REQUIRED_PERMISSION)
    # Command implementation
```

## Database Schema

### Core Tables
- `users` - User accounts with Discord integration
- `tenants` - Regiment/organization records
- `user_tenant_membership` - Many-to-many with roles

### Tenant-Scoped Tables
- `supply_nodes` - Supply locations and inventory
- `production_nodes` - Production facilities
- `logistics_tasks` - Task tracking

All tenant-scoped tables include:
- `tenant_id` foreign key for isolation
- Standard audit fields (created_at, updated_at, is_active)
- Unique constraints combining tenant_id with business keys

## Command Reference

### Tenant Management
- `!setup_regiment` - Register Discord server as tenant
- `!regiment_info` - Show regiment information
- `!add_member @user role` - Add user with role
- `!remove_member @user` - Remove user from regiment
- `!list_members` - List all regiment members

### Logistics Commands
- `!create_supply_node name location type` - Create supply tracking node
- `!create_production_node name location type` - Create production facility
- `!create_task type title description` - Create logistics task
- `!list_tasks [status]` - List tasks with optional filtering
- `!accept_task task_id` - Accept task assignment

### Server Admin Commands
- `!list_tenants` - List all registered tenants
- `!promote_server_admin @user` - Grant server admin privileges

## Configuration

### Environment Variables
- `DISCORD_BOT_TOKEN` - Discord bot token (required)
- `DATABASE_URL` - Database connection string
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `DEFAULT_ADMIN_DISCORD_ID` - Initial server admin user

### Per-Tenant Configuration
Each tenant can have custom JSON configuration stored in the database, accessible via the `Tenant.config` property.

## Deployment Considerations

### Security
- Never commit Discord bot tokens to version control
- Use environment variables for sensitive configuration
- Regularly audit server admin permissions
- Monitor cross-tenant access attempts

### Performance
- Tenant cache for frequently accessed data
- Database connection pooling
- Efficient query patterns with proper indexing

### Monitoring
- Comprehensive logging with tenant context
- Database health checks
- Permission violation alerts
- Usage metrics per tenant