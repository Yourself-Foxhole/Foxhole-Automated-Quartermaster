"""
Multi-tenant Discord bot framework for Foxhole Automated Quartermaster.

This module provides the core Discord bot implementation with multi-tenant
support, command routing, and permission enforcement.
"""

from __future__ import annotations

import logging
import traceback
from typing import Dict, Optional, List, Callable, Any
from functools import wraps

import discord
from discord.ext import commands
from sqlalchemy.orm import Session

from ..core.tenant import TenantManager, Tenant
from ..models import (
    User, TenantContext, UserRole, Permission,
    TenantNotFoundError, UserNotMemberError, TenantPermissionError
)
from ..utils.database import DatabaseManager


logger = logging.getLogger(__name__)


class TenantBot(commands.Bot):
    """
    Multi-tenant Discord bot that routes commands based on guild context
    and enforces tenant-specific permissions.
    """
    
    def __init__(self, command_prefix: str, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            **kwargs
        )
        
        self.db_manager: Optional[DatabaseManager] = None
        self.tenant_manager: Optional[TenantManager] = None
        self._command_permissions: Dict[str, Permission] = {}
        
    async def setup_hook(self) -> None:
        """Initialize database and tenant management on bot startup."""
        logger.info("Setting up multi-tenant Discord bot...")
        
        # Initialize database
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        
        # Initialize tenant manager
        self.tenant_manager = TenantManager(self.db_manager.get_session())
        
        logger.info("Multi-tenant Discord bot setup complete")
    
    def get_db_session(self) -> Session:
        """Get database session for operations."""
        if not self.db_manager:
            raise RuntimeError("Database manager not initialized")
        return self.db_manager.get_session()
    
    async def get_or_create_user(self, discord_user: discord.User) -> User:
        """Get or create a user record from Discord user."""
        session = self.get_db_session()
        
        user = session.query(User).filter(
            User.discord_id == str(discord_user.id)
        ).first()
        
        if not user:
            user = User(
                discord_id=str(discord_user.id),
                username=discord_user.name,
                display_name=discord_user.display_name
            )
            session.add(user)
            session.commit()
            logger.info(f"Created new user: {discord_user.name} ({discord_user.id})")
        
        return user
    
    async def get_tenant_for_guild(self, guild_id: int) -> Optional[Tenant]:
        """Get the tenant associated with a Discord guild."""
        if not self.tenant_manager:
            return None
        return self.tenant_manager.get_tenant_by_discord_guild(str(guild_id))
    
    async def create_tenant_context(
        self, 
        ctx: commands.Context
    ) -> Optional[TenantContext]:
        """Create tenant context from Discord command context."""
        if not ctx.guild:
            return None
            
        tenant = await self.get_tenant_for_guild(ctx.guild.id)
        if not tenant:
            return None
        
        user = await self.get_or_create_user(ctx.author)
        
        if not self.tenant_manager:
            return None
            
        return self.tenant_manager.create_tenant_context(tenant.slug, user)
    
    def require_permission(self, permission: Permission):
        """Decorator to require specific permission for a command."""
        def decorator(func: Callable) -> Callable:
            # Store permission requirement
            self._command_permissions[func.__name__] = permission
            
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract context from args (first arg after self for commands)
                ctx = args[1] if len(args) > 1 else None
                if not isinstance(ctx, commands.Context):
                    raise ValueError("Permission decorator can only be used on bot commands")
                
                # Create tenant context and check permission
                tenant_context = await self.create_tenant_context(ctx)
                if not tenant_context:
                    await ctx.send("❌ This command can only be used in a registered regiment server.")
                    return
                
                if not tenant_context.has_permission(permission):
                    role_name = tenant_context.user_role.value if tenant_context.user_role else "none"
                    await ctx.send(
                        f"❌ You don't have permission to use this command. "
                        f"Required: `{permission.value}`, Your role: `{role_name}`"
                    )
                    return
                
                # Add tenant context to kwargs for the command
                kwargs['tenant_context'] = tenant_context
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def require_role(self, role: UserRole):
        """Decorator to require specific role for a command."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                ctx = args[1] if len(args) > 1 else None
                if not isinstance(ctx, commands.Context):
                    raise ValueError("Role decorator can only be used on bot commands")
                
                tenant_context = await self.create_tenant_context(ctx)
                if not tenant_context:
                    await ctx.send("❌ This command can only be used in a registered regiment server.")
                    return
                
                if tenant_context.user_role != role and tenant_context.user_role != UserRole.SERVER_ADMIN:
                    current_role = tenant_context.user_role.value if tenant_context.user_role else "none"
                    await ctx.send(
                        f"❌ This command requires `{role.value}` role. Your role: `{current_role}`"
                    )
                    return
                
                kwargs['tenant_context'] = tenant_context
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Log which tenants are configured
        if self.tenant_manager:
            for guild in self.guilds:
                tenant = await self.get_tenant_for_guild(guild.id)
                if tenant:
                    logger.info(f'Guild {guild.name} ({guild.id}) -> Tenant {tenant.slug}')
                else:
                    logger.warning(f'Guild {guild.name} ({guild.id}) has no configured tenant')
    
    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        logger.info(f'Joined new guild: {guild.name} ({guild.id})')
        
        # Check if this guild has a configured tenant
        tenant = await self.get_tenant_for_guild(guild.id)
        if not tenant:
            # Send setup instructions to the guild owner or general channel
            try:
                embed = discord.Embed(
                    title="Welcome to Foxhole Automated Quartermaster!",
                    description=(
                        "This bot requires setup before it can be used. "
                        "A server administrator needs to register your regiment as a tenant."
                    ),
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Next Steps",
                    value=(
                        "1. Have a server administrator run `!setup_regiment` to register your regiment\n"
                        "2. Configure your regiment settings\n"
                        "3. Start using the logistics tracking features!"
                    ),
                    inline=False
                )
                
                # Try to send to system channel, then general, then first text channel
                channel = (
                    guild.system_channel or
                    discord.utils.get(guild.text_channels, name='general') or
                    guild.text_channels[0] if guild.text_channels else None
                )
                
                if channel:
                    await channel.send(embed=embed)
                
            except discord.Forbidden:
                logger.warning(f"Could not send welcome message to guild {guild.name}")
    
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Global error handler for commands."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        if isinstance(error, TenantNotFoundError):
            await ctx.send("❌ This server is not registered as a regiment. Use `!setup_regiment` to get started.")
            return
        
        if isinstance(error, UserNotMemberError):
            await ctx.send("❌ You are not a member of this regiment.")
            return
        
        if isinstance(error, TenantPermissionError):
            await ctx.send(f"❌ Permission denied: {str(error)}")
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
            return
        
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {str(error)}")
            return
        
        # Log unexpected errors
        logger.error(f"Unexpected error in command {ctx.command}: {str(error)}")
        logger.error(traceback.format_exc())
        
        await ctx.send("❌ An unexpected error occurred. Please try again later.")


def tenant_command(**kwargs):
    """Decorator to mark a command as tenant-specific."""
    def decorator(func: Callable) -> Callable:
        # Add tenant-specific metadata
        func.__tenant_command__ = True
        return commands.command(**kwargs)(func)
    return decorator


def server_admin_only():
    """Decorator to restrict command to server administrators only."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, ctx: commands.Context, *args, **kwargs):
            user = await self.get_or_create_user(ctx.author)
            if not user.is_server_admin:
                await ctx.send("❌ This command is restricted to server administrators.")
                return
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator