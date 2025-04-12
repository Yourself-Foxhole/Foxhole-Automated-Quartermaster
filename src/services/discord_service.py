"""
Discord service module for handling Discord-specific functionality.

This module provides the DiscordService class which manages:
- Discord client initialization and connection
- Command registration and handling
- Event handling for task-related events
- Message formatting and sending
"""

import os
import logging
from typing import Dict, List, Optional, Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from src.services.task_service import TaskService
from src.models.task import Task, TaskStatus, TaskPriority

logger = logging.getLogger(__name__)

class DiscordService:
    """Service for handling Discord-specific functionality."""
    
    def __init__(self, task_service: TaskService):
        """Initialize the Discord service.
        
        Args:
            task_service: The task service to use for task operations
        """
        self.task_service = task_service
        self.client = commands.Bot(command_prefix="!", intents=discord.Intents.all())
        self._setup_commands()
        self._setup_event_handlers()
        
    def _setup_commands(self):
        """Set up Discord slash commands."""
        @self.client.tree.command(name="task", description="Manage logistics tasks")
        @app_commands.describe(
            action="The action to perform",
            task_id="The ID of the task (for view, claim, update, complete, release)",
            priority="Filter tasks by priority (for list, filter)",
            location="Filter tasks by location (for list, filter)",
            item="Filter tasks by item type (for list, filter)",
            status="Filter tasks by status (for filter)",
            progress="Progress percentage (for update)",
            notes="Additional notes (for update)"
        )
        async def task(
            interaction: discord.Interaction,
            action: str,
            task_id: Optional[str] = None,
            priority: Optional[str] = None,
            location: Optional[str] = None,
            item: Optional[str] = None,
            status: Optional[str] = None,
            progress: Optional[int] = None,
            notes: Optional[str] = None
        ):
            """Handle task-related commands."""
            try:
                if action == "list":
                    await self._handle_list_command(interaction, priority, location, item)
                elif action == "view":
                    if not task_id:
                        await interaction.response.send_message("Task ID is required for viewing a task.", ephemeral=True)
                        return
                    await self._handle_view_command(interaction, task_id)
                elif action == "claim":
                    if not task_id:
                        await interaction.response.send_message("Task ID is required for claiming a task.", ephemeral=True)
                        return
                    await self._handle_claim_command(interaction, task_id)
                elif action == "update":
                    if not task_id or progress is None:
                        await interaction.response.send_message("Task ID and progress are required for updating a task.", ephemeral=True)
                        return
                    await self._handle_update_command(interaction, task_id, progress, notes)
                elif action == "complete":
                    if not task_id:
                        await interaction.response.send_message("Task ID is required for completing a task.", ephemeral=True)
                        return
                    await self._handle_complete_command(interaction, task_id)
                elif action == "release":
                    if not task_id:
                        await interaction.response.send_message("Task ID is required for releasing a task.", ephemeral=True)
                        return
                    await self._handle_release_command(interaction, task_id)
                elif action == "filter":
                    await self._handle_filter_command(interaction, priority, location, item, status)
                else:
                    await interaction.response.send_message(f"Unknown action: {action}", ephemeral=True)
            except Exception as e:
                logger.error(f"Error handling task command: {e}")
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
    
    def _setup_event_handlers(self):
        """Set up Discord event handlers."""
        @self.client.event
        async def on_ready():
            """Handle the on_ready event."""
            logger.info(f"Discord bot is ready. Logged in as {self.client.user}")
            try:
                synced = await self.client.tree.sync()
                logger.info(f"Synced {len(synced)} command(s)")
            except Exception as e:
                logger.error(f"Error syncing commands: {e}")
    
    async def _handle_list_command(self, interaction: discord.Interaction, priority: Optional[str], location: Optional[str], item: Optional[str]):
        """Handle the list command."""
        tasks = await self.task_service.get_tasks(priority=priority, location=location, item=item)
        if not tasks:
            await interaction.response.send_message("No tasks found matching the criteria.", ephemeral=True)
            return
        
        embed = self._create_task_list_embed(tasks)
        await interaction.response.send_message(embed=embed)
    
    async def _handle_view_command(self, interaction: discord.Interaction, task_id: str):
        """Handle the view command."""
        task = await self.task_service.get_task(task_id)
        if not task:
            await interaction.response.send_message(f"Task with ID {task_id} not found.", ephemeral=True)
            return
        
        embed = self._create_task_detail_embed(task)
        await interaction.response.send_message(embed=embed)
    
    async def _handle_claim_command(self, interaction: discord.Interaction, task_id: str):
        """Handle the claim command."""
        user_id = str(interaction.user.id)
        task = await self.task_service.claim_task(task_id, user_id)
        if not task:
            await interaction.response.send_message(f"Failed to claim task {task_id}. It may be already claimed or not exist.", ephemeral=True)
            return
        
        embed = self._create_task_detail_embed(task)
        await interaction.response.send_message(f"You have claimed task {task_id}.", embed=embed)
    
    async def _handle_update_command(self, interaction: discord.Interaction, task_id: str, progress: int, notes: Optional[str]):
        """Handle the update command."""
        user_id = str(interaction.user.id)
        task = await self.task_service.update_task_progress(task_id, user_id, progress, notes)
        if not task:
            await interaction.response.send_message(f"Failed to update task {task_id}. It may not be claimed by you or not exist.", ephemeral=True)
            return
        
        embed = self._create_task_detail_embed(task)
        await interaction.response.send_message(f"Task {task_id} progress updated to {progress}%.", embed=embed)
    
    async def _handle_complete_command(self, interaction: discord.Interaction, task_id: str):
        """Handle the complete command."""
        user_id = str(interaction.user.id)
        task = await self.task_service.complete_task(task_id, user_id)
        if not task:
            await interaction.response.send_message(f"Failed to complete task {task_id}. It may not be claimed by you or not exist.", ephemeral=True)
            return
        
        embed = self._create_task_detail_embed(task)
        await interaction.response.send_message(f"Task {task_id} has been marked as completed.", embed=embed)
    
    async def _handle_release_command(self, interaction: discord.Interaction, task_id: str):
        """Handle the release command."""
        user_id = str(interaction.user.id)
        task = await self.task_service.release_task(task_id, user_id)
        if not task:
            await interaction.response.send_message(f"Failed to release task {task_id}. It may not be claimed by you or not exist.", ephemeral=True)
            return
        
        embed = self._create_task_detail_embed(task)
        await interaction.response.send_message(f"Task {task_id} has been released back to the pool.", embed=embed)
    
    async def _handle_filter_command(self, interaction: discord.Interaction, priority: Optional[str], location: Optional[str], item: Optional[str], status: Optional[str]):
        """Handle the filter command."""
        tasks = await self.task_service.get_tasks(priority=priority, location=location, item=item, status=status)
        if not tasks:
            await interaction.response.send_message("No tasks found matching the criteria.", ephemeral=True)
            return
        
        embed = self._create_task_list_embed(tasks)
        await interaction.response.send_message(embed=embed)
    
    def _create_task_list_embed(self, tasks: List[Task]) -> discord.Embed:
        """Create a Discord embed for a list of tasks."""
        embed = discord.Embed(
            title="Logistics Task Board",
            description="Available tasks for logistics operations",
            color=discord.Color.blue()
        )
        
        # Group tasks by priority
        critical_tasks = [t for t in tasks if t.priority >= 8]
        priority_tasks = [t for t in tasks if 5 <= t.priority < 8]
        optional_tasks = [t for t in tasks if t.priority < 5]
        
        if critical_tasks:
            critical_text = "\n".join([f"Task #{t.id}: {t.description}" for t in critical_tasks])
            embed.add_field(name="🔴 Critical Tasks", value=critical_text, inline=False)
        
        if priority_tasks:
            priority_text = "\n".join([f"Task #{t.id}: {t.description}" for t in priority_tasks])
            embed.add_field(name="🟡 Priority Tasks", value=priority_text, inline=False)
        
        if optional_tasks:
            optional_text = "\n".join([f"Task #{t.id}: {t.description}" for t in optional_tasks])
            embed.add_field(name="💚 Optional Tasks", value=optional_text, inline=False)
        
        embed.set_footer(text="Use /task claim <id> to claim a task")
        return embed
    
    def _create_task_detail_embed(self, task: Task) -> discord.Embed:
        """Create a Discord embed for a single task."""
        # Determine color based on priority
        if task.priority >= 8:
            color = discord.Color.red()
            priority_text = "🔴 Critical"
        elif task.priority >= 5:
            color = discord.Color.yellow()
            priority_text = "🟡 Priority"
        else:
            color = discord.Color.green()
            priority_text = "💚 Optional"
        
        embed = discord.Embed(
            title=f"Task #{task.id}: {task.description}",
            description=task.notes or "No additional notes",
            color=color
        )
        
        embed.add_field(name="Item", value=f"{task.item_name} ({task.item_quantity})", inline=True)
        embed.add_field(name="Priority", value=f"{priority_text} ({task.priority}/10)", inline=True)
        embed.add_field(name="Status", value=task.status.value, inline=True)
        embed.add_field(name="Source", value=f"{task.source_location} ({task.source_building})", inline=True)
        embed.add_field(name="Destination", value=f"{task.destination_location} ({task.destination_building})", inline=True)
        embed.add_field(name="Estimated Time", value=f"{task.estimated_time} minutes", inline=True)
        
        if task.claimed_by:
            embed.add_field(name="Claimed By", value=f"<@{task.claimed_by}>", inline=True)
            embed.add_field(name="Claimed At", value=task.claimed_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        # Add auto-release information if task is claimed
        if task.status in [TaskStatus.CLAIMED, TaskStatus.IN_PROGRESS]:
            time_remaining = (task.auto_release - task.claimed_at).total_seconds() / 60
            embed.set_footer(text=f"Auto-releases in {int(time_remaining)} minutes if no progress")
        
        return embed
    
    async def start(self):
        """Start the Discord bot."""
        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            raise ValueError("DISCORD_TOKEN environment variable is not set")
        
        await self.client.start(token)
    
    async def stop(self):
        """Stop the Discord bot."""
        await self.client.close() 