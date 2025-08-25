"""
Discord bot integration with the presentation layer.

This module shows how to integrate the EmbedRenderer with Discord bot commands.
to send formatted messages using Jinja2 templates.
"""

import logging
from datetime import datetime
from typing import Optional

import disnake
from disnake.ext import commands
from disnake.ext.commands import CommandSyncFlags

# Import the presentation layer
from presentation import EmbedRenderer
# Import existing services
from services.tasks.task import Task, TaskStatus


class FoxholeBot(commands.Bot):
    """
    Foxhole Automated Quartermaster Discord Bot with presentation layer integration.
    
    This bot shows how to use the EmbedRenderer to send formatted messages
    for various logistics operations.
    """
    
    def __init__(self, *args, **kwargs):
        # Remove deprecated sync_commands if present
        kwargs.pop('sync_commands', None)
        # Add command_sync_flags if not present
        if 'command_sync_flags' not in kwargs:
            kwargs['command_sync_flags'] = CommandSyncFlags.default()
        super().__init__(*args, **kwargs)
        self.embed_renderer = EmbedRenderer()
        self.logger = logging.getLogger(__name__)
    
    async def on_ready(self):
        """Called when the bot is ready."""
        self.logger.info("Bot %s is ready!", self.user)
    
    @commands.slash_command(name="task_status", description="Get status of a logistics task")
    async def task_status(self, inter: disnake.ApplicationCommandInteraction, task_id: str):
        """
        Display the status of a logistics task using the presentation layer.
        
        Args:
            inter: Discord interaction object.
            task_id: ID of the task to display.
        """
        await inter.response.defer()
        
        try:
            # Mock task data for demonstration (in real implementation, this would come from the database)
            task = self._get_mock_task(task_id)
            
            if task is None:
                embed = disnake.Embed(
                    title="❌ Task Not Found",
                    description=f"No task found with ID: `{task_id}`",
                    color=0xff0000
                )
                await inter.followup.send(embed=embed)
                return
            
            # Use the presentation layer to render the task update
            embed = self.embed_renderer.render_task_update(task)
            await inter.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error("Error displaying task status: %s", e)
            error_embed = disnake.Embed(
                title="❌ Error",
                description="Failed to retrieve task status.",
                color=0xff0000
            )
            await inter.followup.send(embed=error_embed)
    
    @commands.slash_command(name="inventory_update", description="Simulate an inventory delta")
    async def inventory_update(self, inter: disnake.ApplicationCommandInteraction, 
                             facility: str = "Reaching Trail Depot"):
        """
        Display a mock inventory delta using the presentation layer.
        
        Args:
            inter: Discord interaction object.
            facility: Name of the facility for the demo.
        """
        await inter.response.defer()
        
        try:
            # Mock inventory changes for demonstration
            changes = {
                "7.62mm": -150,
                "40mm": +50,
                "Bandages": +25,
                "BMats": -200,
                "Diesel": +100
            }
            
            embed = self.embed_renderer.render_inventory_delta(
                facility_name=facility,
                changes=changes,
                region="Deadlands",
                critical_items=["7.62mm", "BMats"],
                production_impact="Ammunition production may be affected"
            )
            
            await inter.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error("Error displaying inventory update: %s", e)
            error_embed = disnake.Embed(
                title="❌ Error",
                description="Failed to display inventory update.",
                color=0xff0000
            )
            await inter.followup.send(embed=error_embed)
    
    @commands.slash_command(name="alert", description="Send a logistics alert")
    async def send_alert(self, inter: disnake.ApplicationCommandInteraction,
                        alert_type: str = commands.Param(choices=["critical", "warning", "info"]),
                        message: str = "Critical supply shortage detected"):
        """
        Send a logistics alert using the presentation layer.
        
        Args:
            inter: Discord interaction object.
            alert_type: Type of alert to send.
            message: Alert message content.
        """
        await inter.response.defer()
        
        try:
            # Generate alert based on type
            if alert_type == "critical":
                title = "Critical Supply Shortage"
                kwargs = {
                    "location": "Deadlands - Reaching Trail",
                    "priority": "urgent",
                    "affected_items": ["7.62mm", "40mm", "Bandages"],
                    "supply_shortage": {"7.62mm": 500, "40mm": 200, "Bandages": 100},
                    "recommended_actions": [
                        "Immediate resupply from Westgate depot",
                        "Redirect production from Safe House facility",
                        "Request logi run from clan members"
                    ],
                    "frontline_impact": "Frontline operations in Deadlands may be compromised within 2 hours",
                    "estimated_resolution": "45-60 minutes",
                    "alert_id": "FAQ-2024-001"
                }
            elif alert_type == "warning":
                title = "Low Stock Warning"
                kwargs = {
                    "location": "Westgate - Safe House Storage",
                    "priority": "medium",
                    "affected_items": ["Shirts", "BMats"],
                    "recommended_actions": [
                        "Monitor stock levels closely",
                        "Schedule production run within 4 hours"
                    ],
                    "estimated_resolution": "2-3 hours",
                    "alert_id": "FAQ-2024-002"
                }
            else:  # info
                title = "Logistics Update"
                kwargs = {
                    "location": "Multiple Facilities",
                    "priority": "low",
                    "recommended_actions": ["Review daily production reports"],
                    "alert_id": "FAQ-2024-003"
                }
            
            embed = self.embed_renderer.render_alert(
                alert_title=title,
                alert_message=message,
                alert_type=alert_type,
                **kwargs
            )
            
            await inter.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error("Error sending alert: %s", e)
            error_embed = disnake.Embed(
                title="❌ Error",
                description="Failed to send alert.",
                color=0xff0000
            )
            await inter.followup.send(embed=error_embed)
    
    def _get_mock_task(self, task_id: str) -> Optional[Task]:
        """
        Get a mock task for demonstration purposes.
        
        Args:
            task_id: ID of the task to retrieve.
            
        Returns:
            Mock Task object or None if not found.
        """
        # Mock task data based on task_id
        mock_tasks = {
            "PROD-001": Task(
                task_id="PROD-001",
                name="Produce 7.62mm Ammunition",
                task_type="production",
                status=TaskStatus.IN_PROGRESS,
                base_priority=2.5,
                created_at=datetime(2024, 1, 15, 14, 30),
                metadata={
                    "target_quantity": 1000,
                    "current_progress": 650,
                    "facility": "Safe House Assembly",
                    "estimated_completion": "45 minutes"
                }
            ),
            "TRANS-001": Task(
                task_id="TRANS-001", 
                name="Transport Supplies to Deadlands",
                task_type="transport",
                status=TaskStatus.BLOCKED,
                base_priority=3.0,
                created_at=datetime(2024, 1, 15, 13, 15),
                metadata={
                    "origin": "Westgate Depot",
                    "destination": "Reaching Trail Storage",
                    "cargo": "Mixed ammunition and medical supplies",
                    "blocker": "Route contested — waiting for frontline stabilization"
                }
            ),
            "SUP-001": Task(
                task_id="SUP-001",
                name="Resupply Frontline Bunker Base",
                task_type="supply",
                status=TaskStatus.COMPLETED,
                base_priority=4.0,
                created_at=datetime(2024, 1, 15, 12, 0),
                metadata={
                    "location": "Deadlands FOB-7",
                    "items_delivered": "500x 7.62mm, 200x 40mm, 100x Bandages",
                    "completion_time": "2024-01-15 15:30"
                }
            )
        }
        
        task = mock_tasks.get(task_id)
        if task and task.status == TaskStatus.BLOCKED:
            task.mark_blocked()
        elif task and task_id == "SUP-001":
            # Add some order associations for the completed task
            task.add_order("ORD-123")
            task.add_order("ORD-124")
        
        return task


# Function to run the bot -- used by main.py or testing
def create_bot(token: str) -> FoxholeBot:
    """
    Create and configure the Foxhole bot.
    
    Args:
        token: Discord bot token.
        
    Returns:
        Configured FoxholeBot instance.
    """
    bot = FoxholeBot(
        command_prefix="!",
        intents=intents
    )
    
    return bot


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set.")
    
    bot = create_bot(token)
    bot.run(token)