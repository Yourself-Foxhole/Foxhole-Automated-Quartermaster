"""
Logistics tracking commands for supply chains and task management.
"""

import json
import logging
from typing import Optional, Dict, Any

import discord
from discord.ext import commands

from ..core.bot import TenantBot, tenant_command
from ..models import TenantContext, Permission


logger = logging.getLogger(__name__)


class LogisticsCommands(commands.Cog):
    """Commands for logistics tracking and supply chain management."""
    
    def __init__(self, bot: TenantBot):
        self.bot = bot
    
    @tenant_command(name='create_supply_node')
    async def create_supply_node(
        self,
        ctx: commands.Context,
        name: str,
        location: str,
        node_type: str = "Storage",
        tenant_context: Optional[TenantContext] = None
    ):
        """
        Create a new supply node for tracking inventory.
        
        Usage: !create_supply_node "Main Depot" "Deadlands" "Storage Depot"
        """
        if not tenant_context:
            return
        
        tenant_context.require_permission(Permission.EDIT_SUPPLY_GRAPH)
        
        tenant = self.bot.tenant_manager.get_tenant_by_slug(tenant_context.tenant_slug)
        
        try:
            supply_node = tenant.create_supply_node(name, location, node_type)
            
            embed = discord.Embed(
                title="✅ Supply Node Created",
                description=f"Created supply node: **{name}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Location", value=location, inline=True)
            embed.add_field(name="Type", value=node_type, inline=True)
            embed.add_field(name="Node ID", value=str(supply_node.id), inline=True)
            
            await ctx.send(embed=embed)
            logger.info(f"Created supply node {name} for tenant {tenant.slug}")
            
        except Exception as e:
            logger.error(f"Error creating supply node: {e}")
            await ctx.send(f"❌ Failed to create supply node: {str(e)}")
    
    @tenant_command(name='list_supply_nodes')
    async def list_supply_nodes(
        self,
        ctx: commands.Context,
        tenant_context: Optional[TenantContext] = None
    ):
        """List all supply nodes for this regiment."""
        if not tenant_context:
            return
        
        tenant_context.require_permission(Permission.VIEW_TENANT_DATA)
        
        tenant = self.bot.tenant_manager.get_tenant_by_slug(tenant_context.tenant_slug)
        supply_nodes = tenant.get_supply_nodes()
        
        if not supply_nodes:
            await ctx.send("❌ No supply nodes found. Create one with `!create_supply_node`.")
            return
        
        embed = discord.Embed(
            title=f"📦 Supply Nodes ({len(supply_nodes)})",
            color=discord.Color.blue()
        )
        
        for node in supply_nodes[:10]:  # Limit to first 10 to avoid message size limits
            embed.add_field(
                name=node.name,
                value=(
                    f"**Location:** {node.location}\n"
                    f"**Type:** {node.node_type}\n"
                    f"**Status:** {'Active' if node.is_active else 'Inactive'}"
                ),
                inline=True
            )
        
        if len(supply_nodes) > 10:
            embed.set_footer(text=f"Showing 10 of {len(supply_nodes)} nodes")
        
        await ctx.send(embed=embed)
    
    @tenant_command(name='create_production_node')
    async def create_production_node(
        self,
        ctx: commands.Context,
        name: str,
        location: str,
        facility_type: str = "Factory",
        tenant_context: Optional[TenantContext] = None
    ):
        """
        Create a new production facility for tracking manufacturing.
        
        Usage: !create_production_node "Factory Alpha" "Godcrofts" "Mass Production Factory"
        """
        if not tenant_context:
            return
        
        tenant_context.require_permission(Permission.EDIT_PRODUCTION_GRAPH)
        
        tenant = self.bot.tenant_manager.get_tenant_by_slug(tenant_context.tenant_slug)
        
        try:
            production_node = tenant.create_production_node(name, location, facility_type)
            
            embed = discord.Embed(
                title="✅ Production Node Created",
                description=f"Created production facility: **{name}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Location", value=location, inline=True)
            embed.add_field(name="Facility Type", value=facility_type, inline=True)
            embed.add_field(name="Node ID", value=str(production_node.id), inline=True)
            
            await ctx.send(embed=embed)
            logger.info(f"Created production node {name} for tenant {tenant.slug}")
            
        except Exception as e:
            logger.error(f"Error creating production node: {e}")
            await ctx.send(f"❌ Failed to create production node: {str(e)}")
    
    @tenant_command(name='list_production_nodes')
    async def list_production_nodes(
        self,
        ctx: commands.Context,
        tenant_context: Optional[TenantContext] = None
    ):
        """List all production facilities for this regiment."""
        if not tenant_context:
            return
        
        tenant_context.require_permission(Permission.VIEW_TENANT_DATA)
        
        tenant = self.bot.tenant_manager.get_tenant_by_slug(tenant_context.tenant_slug)
        production_nodes = tenant.get_production_nodes()
        
        if not production_nodes:
            await ctx.send("❌ No production nodes found. Create one with `!create_production_node`.")
            return
        
        embed = discord.Embed(
            title=f"🏭 Production Nodes ({len(production_nodes)})",
            color=discord.Color.blue()
        )
        
        for node in production_nodes[:10]:  # Limit to first 10
            embed.add_field(
                name=node.name,
                value=(
                    f"**Location:** {node.location}\n"
                    f"**Type:** {node.facility_type}\n"
                    f"**Status:** {'Active' if node.is_active else 'Inactive'}"
                ),
                inline=True
            )
        
        if len(production_nodes) > 10:
            embed.set_footer(text=f"Showing 10 of {len(production_nodes)} nodes")
        
        await ctx.send(embed=embed)
    
    @tenant_command(name='create_task')
    async def create_task(
        self,
        ctx: commands.Context,
        task_type: str,
        title: str,
        *,
        description: str = "",
        tenant_context: Optional[TenantContext] = None
    ):
        """
        Create a new logistics task.
        
        Usage: !create_task Transport "Move shirts to frontline" description: Transport 200 shirts from depot to frontline
        """
        if not tenant_context:
            return
        
        tenant_context.require_permission(Permission.ASSIGN_TASKS)
        
        tenant = self.bot.tenant_manager.get_tenant_by_slug(tenant_context.tenant_slug)
        
        # Get the user who created the task
        user = await self.bot.get_or_create_user(ctx.author)
        
        try:
            task = tenant.create_logistics_task(
                title=title,
                description=description,
                task_type=task_type,
                creator=user
            )
            
            embed = discord.Embed(
                title="✅ Logistics Task Created",
                description=f"**{title}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Type", value=task_type, inline=True)
            embed.add_field(name="Status", value="Pending", inline=True)
            embed.add_field(name="Created by", value=ctx.author.display_name, inline=True)
            
            if description:
                embed.add_field(name="Description", value=description, inline=False)
            
            embed.add_field(name="Task ID", value=str(task.id), inline=True)
            
            await ctx.send(embed=embed)
            logger.info(f"Created task {title} for tenant {tenant.slug}")
            
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            await ctx.send(f"❌ Failed to create task: {str(e)}")
    
    @tenant_command(name='list_tasks')
    async def list_tasks(
        self,
        ctx: commands.Context,
        status: str = None,
        tenant_context: Optional[TenantContext] = None
    ):
        """
        List logistics tasks, optionally filtered by status.
        
        Usage: !list_tasks [status]
        Statuses: pending, in_progress, completed, cancelled
        """
        if not tenant_context:
            return
        
        tenant_context.require_permission(Permission.VIEW_TASKS)
        
        tenant = self.bot.tenant_manager.get_tenant_by_slug(tenant_context.tenant_slug)
        tasks = tenant.get_logistics_tasks(status=status)
        
        if not tasks:
            status_text = f" with status '{status}'" if status else ""
            await ctx.send(f"❌ No tasks found{status_text}.")
            return
        
        embed = discord.Embed(
            title=f"📋 Logistics Tasks ({len(tasks)})",
            color=discord.Color.blue()
        )
        
        if status:
            embed.description = f"Filtered by status: **{status}**"
        
        for task in tasks[:10]:  # Limit to first 10
            # Get creator name
            creator = "Unknown"
            if task.creator:
                try:
                    discord_user = self.bot.get_user(int(task.creator.discord_id))
                    creator = discord_user.display_name if discord_user else task.creator.username
                except:
                    creator = task.creator.username
            
            assignee_text = "Unassigned"
            if task.assignee:
                try:
                    discord_assignee = self.bot.get_user(int(task.assignee.discord_id))
                    assignee_text = discord_assignee.display_name if discord_assignee else task.assignee.username
                except:
                    assignee_text = task.assignee.username
            
            embed.add_field(
                name=f"{task.title} ({task.status})",
                value=(
                    f"**Type:** {task.task_type}\n"
                    f"**Created by:** {creator}\n"
                    f"**Assigned to:** {assignee_text}\n"
                    f"**Priority:** {task.priority}"
                ),
                inline=True
            )
        
        if len(tasks) > 10:
            embed.set_footer(text=f"Showing 10 of {len(tasks)} tasks")
        
        await ctx.send(embed=embed)
    
    @tenant_command(name='accept_task')
    async def accept_task(
        self,
        ctx: commands.Context,
        task_id: str,
        tenant_context: Optional[TenantContext] = None
    ):
        """
        Accept a logistics task assignment.
        
        Usage: !accept_task <task_id>
        """
        if not tenant_context:
            return
        
        tenant_context.require_permission(Permission.ACCEPT_TASKS)
        
        # This would require additional implementation to find and update tasks
        # For now, showing the interface
        await ctx.send(f"✅ Task {task_id} accepted! (Implementation pending)")


async def setup(bot: TenantBot):
    """Add the logistics commands cog to the bot."""
    await bot.add_cog(LogisticsCommands(bot))