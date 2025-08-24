"""
Basic tenant management commands for Discord bot.
"""

import logging
from typing import Optional

import discord
from discord.ext import commands

from ..core.bot import TenantBot, tenant_command, server_admin_only
from ..core.tenant import TenantManager
from ..models import User, UserRole, Permission, TenantContext


logger = logging.getLogger(__name__)


class TenantCommands(commands.Cog):
    """Commands for tenant (regiment) management."""
    
    def __init__(self, bot: TenantBot):
        self.bot = bot
    
    @tenant_command(name='setup_regiment')
    async def setup_regiment(
        self, 
        ctx: commands.Context, 
        name: str, 
        slug: str, 
        faction: str = None
    ):
        """
        Register this Discord server as a new regiment tenant.
        
        Usage: !setup_regiment "My Regiment" my-regiment Colonial
        """
        if not ctx.guild:
            await ctx.send("❌ This command can only be used in a server.")
            return
        
        # Check if user has manage server permission
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send("❌ You need 'Manage Server' permission to set up a regiment.")
            return
        
        try:
            user = await self.bot.get_or_create_user(ctx.author)
            
            tenant = self.bot.tenant_manager.create_tenant(
                name=name,
                slug=slug,
                discord_guild_id=str(ctx.guild.id),
                creator_user=user,
                faction=faction,
                description=f"Regiment for Discord server: {ctx.guild.name}"
            )
            
            embed = discord.Embed(
                title="🎉 Regiment Registered Successfully!",
                description=f"**{name}** has been registered as a new regiment.",
                color=discord.Color.green()
            )
            embed.add_field(name="Regiment Slug", value=slug, inline=True)
            embed.add_field(name="Faction", value=faction or "Not specified", inline=True)
            embed.add_field(name="Your Role", value="Regiment Admin", inline=True)
            embed.add_field(
                name="Next Steps",
                value=(
                    "• Add members with `!add_member @user <role>`\n"
                    "• Configure supply nodes with `!create_supply_node`\n"
                    "• Set up production facilities with `!create_production_node`\n"
                    "• Start tracking logistics with `!create_task`"
                ),
                inline=False
            )
            
            await ctx.send(embed=embed)
            logger.info(f"New tenant created: {slug} for guild {ctx.guild.id}")
            
        except ValueError as e:
            await ctx.send(f"❌ Failed to create regiment: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating tenant: {e}")
            await ctx.send("❌ An error occurred while setting up the regiment.")
    
    @tenant_command(name='regiment_info')
    async def regiment_info(self, ctx: commands.Context):
        """Show information about the current regiment."""
        tenant_context = await self.bot.create_tenant_context(ctx)
        if not tenant_context:
            await ctx.send("❌ This server is not registered as a regiment.")
            return
        
        tenant = self.bot.tenant_manager.get_tenant_by_slug(tenant_context.tenant_slug)
        if not tenant:
            await ctx.send("❌ Regiment not found.")
            return
        
        members = tenant.list_all_members()
        member_summary = {}
        for member in members:
            role = member['role']
            member_summary[role] = member_summary.get(role, 0) + 1
        
        embed = discord.Embed(
            title=f"📋 Regiment: {tenant.name}",
            description=tenant.model.description or "No description set",
            color=discord.Color.blue()
        )
        embed.add_field(name="Slug", value=tenant.slug, inline=True)
        embed.add_field(name="Faction", value=tenant.faction or "Not specified", inline=True)
        embed.add_field(name="Total Members", value=str(len(members)), inline=True)
        
        if member_summary:
            role_breakdown = "\n".join([
                f"• {role.replace('_', ' ').title()}: {count}"
                for role, count in member_summary.items()
            ])
            embed.add_field(name="Members by Role", value=role_breakdown, inline=False)
        
        embed.add_field(
            name="Your Role",
            value=tenant_context.user_role.value.replace('_', ' ').title() if tenant_context.user_role else "None",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @tenant_command(name='add_member')
    @commands.has_permissions(manage_guild=True)
    async def add_member(
        self, 
        ctx: commands.Context, 
        member: discord.Member, 
        role: str,
        tenant_context: Optional[TenantContext] = None
    ):
        """
        Add a member to the regiment with specified role.
        
        Usage: !add_member @username end_user
        Roles: server_admin, regiment_admin, logistics_manager, end_user
        """
        if not tenant_context:
            await ctx.send("❌ This server is not registered as a regiment.")
            return
        
        # Validate role
        try:
            user_role = UserRole(role)
        except ValueError:
            valid_roles = [r.value for r in UserRole]
            await ctx.send(f"❌ Invalid role. Valid roles: {', '.join(valid_roles)}")
            return
        
        # Check permission to add members
        tenant_context.require_permission(Permission.MANAGE_TENANT_USERS)
        
        tenant = self.bot.tenant_manager.get_tenant_by_slug(tenant_context.tenant_slug)
        new_user = await self.bot.get_or_create_user(member)
        
        if tenant.add_member(new_user, user_role):
            embed = discord.Embed(
                title="✅ Member Added",
                description=f"{member.mention} has been added to the regiment as **{user_role.value.replace('_', ' ').title()}**",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ {member.mention} is already a member of this regiment.")
    
    @tenant_command(name='remove_member')
    @commands.has_permissions(manage_guild=True)
    async def remove_member(
        self, 
        ctx: commands.Context, 
        member: discord.Member,
        tenant_context: Optional[TenantContext] = None
    ):
        """Remove a member from the regiment."""
        if not tenant_context:
            return
        
        tenant_context.require_permission(Permission.MANAGE_TENANT_USERS)
        
        tenant = self.bot.tenant_manager.get_tenant_by_slug(tenant_context.tenant_slug)
        user_to_remove = await self.bot.get_or_create_user(member)
        
        if tenant.remove_member(user_to_remove):
            embed = discord.Embed(
                title="✅ Member Removed",
                description=f"{member.mention} has been removed from the regiment",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ {member.mention} is not a member of this regiment.")
    
    @tenant_command(name='list_members')
    async def list_members(
        self, 
        ctx: commands.Context,
        tenant_context: Optional[TenantContext] = None
    ):
        """List all members of the regiment."""
        if not tenant_context:
            return
        
        tenant_context.require_permission(Permission.VIEW_TENANT_DATA)
        
        tenant = self.bot.tenant_manager.get_tenant_by_slug(tenant_context.tenant_slug)
        members = tenant.list_all_members()
        
        if not members:
            await ctx.send("❌ No members found in this regiment.")
            return
        
        embed = discord.Embed(
            title=f"👥 Regiment Members ({len(members)})",
            color=discord.Color.blue()
        )
        
        # Group members by role
        by_role = {}
        for member in members:
            role = member['role']
            if role not in by_role:
                by_role[role] = []
            by_role[role].append(member)
        
        for role, role_members in by_role.items():
            member_list = "\n".join([
                f"• {m['display_name'] or m['username']}"
                for m in role_members
            ])
            embed.add_field(
                name=f"{role.value.replace('_', ' ').title()} ({len(role_members)})",
                value=member_list or "None",
                inline=True
            )
        
        await ctx.send(embed=embed)


class ServerAdminCommands(commands.Cog):
    """Commands restricted to server administrators."""
    
    def __init__(self, bot: TenantBot):
        self.bot = bot
    
    @commands.command(name='list_tenants')
    @server_admin_only()
    async def list_tenants(self, ctx: commands.Context):
        """List all registered tenants (server admin only)."""
        session = self.bot.get_db_session()
        from ..models import Tenant as TenantModel
        
        tenants = session.query(TenantModel).filter(
            TenantModel.is_active == True
        ).all()
        
        if not tenants:
            await ctx.send("No tenants registered.")
            return
        
        embed = discord.Embed(
            title="🏛️ Registered Tenants",
            color=discord.Color.purple()
        )
        
        for tenant_model in tenants:
            guild = self.bot.get_guild(int(tenant_model.discord_guild_id))
            guild_name = guild.name if guild else "Unknown Guild"
            
            embed.add_field(
                name=tenant_model.name,
                value=(
                    f"**Slug:** {tenant_model.slug}\n"
                    f"**Guild:** {guild_name}\n"
                    f"**Faction:** {tenant_model.faction or 'Not set'}"
                ),
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='promote_server_admin')
    @server_admin_only()
    async def promote_server_admin(self, ctx: commands.Context, user: discord.User):
        """Promote a user to server administrator."""
        target_user = await self.bot.get_or_create_user(user)
        target_user.is_server_admin = True
        
        session = self.bot.get_db_session()
        session.commit()
        
        await ctx.send(f"✅ {user.mention} has been promoted to server administrator.")


async def setup(bot: TenantBot):
    """Add the command cogs to the bot."""
    await bot.add_cog(TenantCommands(bot))
    await bot.add_cog(ServerAdminCommands(bot))