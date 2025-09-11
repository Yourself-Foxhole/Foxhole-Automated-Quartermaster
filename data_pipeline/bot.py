"""Discord bot integration with the presentation layer.

This module shows how to integrate the EmbedRenderer with Discord bot commands.
to send formatted messages using Jinja2 templates.
"""

import logging
from datetime import UTC, datetime

import disnake

from data.discord.discord import DiscordBot
from presentation import EmbedRenderer
from services.tasks.task import Task, TaskStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Define Discord intents explicitly
DEFAULT_INTENTS = disnake.Intents.default()
# Uncomment the following if you need privileged intents:
# DEFAULT_INTENTS.members = True
# DEFAULT_INTENTS.message_content = True

ERROR_TITLE = "❌ Error"


class FoxholeBot:
    """Foxhole Automated Quartermaster Discord Bot with presentation layer integration.

    This bot uses DiscordBot for connection, event handling, and messaging,
    and integrates the EmbedRenderer for logistics operations.
    """  # noqa: E501, RUF100

    def __init__(self, bot_token: str | None = None, intents: disnake.Intents = DEFAULT_INTENTS) -> None:
        """Initialize the FoxholeBot with presentation layer integration.

        Args:
            bot_token: The Discord bot token.
            intents: Discord Intents object.

        """
        self.token: str | None = bot_token
        self.intents = intents
        self.discord_bot = DiscordBot(token=bot_token, intents=intents)
        self.embed_renderer = EmbedRenderer()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing FoxholeBot...")
        # Register event handlers
        self.discord_bot.register_on_ready(self.on_ready)
        self.discord_bot.register_on_message(self.on_message)

    def run(self) -> None:
        """Start the Discord bot."""
        self.discord_bot.run()

    def shutdown(self) -> None:
        """Shutdown the Discord bot."""
        self.discord_bot.shutdown(None)

    def is_connected(self) -> bool:
        """Check if the bot is connected to Discord."""
        return self.discord_bot.is_connected()

    async def on_ready(self) -> None:
        """Handle the event when the bot is ready and connected to Discord."""
        await self.discord_bot.send_message(
            self.discord_bot.get_default_channel_id(),
            "FoxholeBot is online and ready!",
        )
        self.logger.info("Bot is ready! (user: %s)", getattr(self.discord_bot.client, "user", None))

    async def on_message(self, message: disnake.Message) -> None:
        """Handle incoming Discord messages and dispatch to appropriate command handlers.

        Args:
            message: The incoming Discord message object.

        """
        # Ignore messages from the bot itself
        if message.author == getattr(self.discord_bot.client, "user", None):
            return
        content = message.content.strip()
        if content.startswith("/task_status"):
            await self._handle_task_status(message)
        elif content.startswith("/inventory_update"):
            await self._handle_inventory_update(message)
        elif content.startswith("/alert"):
            await self._handle_alert(message)
        elif content.startswith("/onboard_network"):
            await self._handle_onboard_network(message)

    async def _handle_task_status(self, message):
        parts = message.content.strip().split()
        if len(parts) < 2:
            await self.discord_bot.send_message(
                message.channel.id,
                "Usage: /task_status <task_id>",
            )
            return
        task_id = parts[1]
        try:
            task = self._get_mock_task(task_id)
            if not task:
                embed = disnake.Embed(
                    title="❌ Task Not Found",
                    description=f"No task found with ID: `{task_id}`",
                    color=0xff0000,
                )
                await self.discord_bot.send_message(
                    message.channel.id,
                    content="",
                    embed=embed,
                )
                return
            embed = self.embed_renderer.render_task_update(task)
            await self.discord_bot.send_message(
                message.channel.id,
                content="",
                embed=embed,
            )
        except (AttributeError, ValueError, TypeError) as e:
            self.logger.error("Error displaying task status: %s", e)
            error_embed = disnake.Embed(
                title="❌ Error",
                description="Failed to retrieve task status.",
                color=0xff0000,
            )
            await self.discord_bot.send_message(
                message.channel.id,
                content="",
                embed=error_embed,
            )

    async def _handle_inventory_update(self, message):
        parts = message.content.strip().split(maxsplit=1)
        facility = parts[1] if len(parts) > 1 else "Reaching Trail Depot"
        changes = {
            "7.62mm": -150,
            "40mm": +50,
            "Bandages": +25,
            "BMats": -200,
            "Diesel": +100,
        }
        try:
            embed = self.embed_renderer.render_inventory_delta(
                facility_name=facility,
                changes=changes,
                region="Deadlands",
                critical_items=["7.62mm", "BMats"],
                production_impact="Ammunition production may be affected",
            )
        except (AttributeError, ValueError, TypeError) as e:
            self.logger.error("Error displaying inventory update: %s", e)
            error_embed = disnake.Embed(
                title=ERROR_TITLE,
                description="Failed to display inventory update.",
                color=0xff0000,
            )
            await self.discord_bot.send_message(message.channel.id, embed=error_embed)
            return
        await self.discord_bot.send_message(message.channel.id, embed=embed)

    async def _handle_alert(self, message):
        # Example: /alert critical <message>
        parts = message.content.strip().split(maxsplit=2)
        alert_type = parts[1] if len(parts) > 1 else "critical"
        alert_message = parts[2] if len(parts) > 2 else "Critical supply shortage detected"
        try:
            title, kwargs = self._get_alert_details(alert_type)
        except (KeyError, AttributeError, ValueError) as e:
            self.logger.error("Error getting alert details: %s", e)
            error_embed = disnake.Embed(
                title=ERROR_TITLE,
                description="Failed to get alert details.",
                color=0xff0000,
            )
            await self.discord_bot.send_message(message.channel.id, embed=error_embed)
            return

        try:
            embed = self.embed_renderer.render_alert(
                alert_title=title,
                alert_message=alert_message,
                alert_type=alert_type,
                **kwargs,
            )
    async def _handle_onboard_network(self, message):
        # Example: /onboard_network <node_name> <location> <type>
        parts = message.content.strip().split(maxsplit=3)
            await self.discord_bot.send_message(
                message.channel.id,
                "Usage: /onboard_network <node_name> <location> [type]"
            )
            await self.discord_bot.send_message(message.channel.id, "Usage: /onboard_network <node_name> <location> [type]")
            return
        node_name = parts[1]
        try:
            embed = self.embed_renderer.render_alert(
                alert_title=title,
                alert_message=alert_message,
                alert_type=alert_type,
                **kwargs,
            )
            await self.discord_bot.send_message(message.channel.id, embed=embed)
        except (AttributeError, ValueError, TypeError) as e:
            self.logger.error("Error displaying alert: %s", e)
            error_embed = disnake.Embed(
                title=ERROR_TITLE,
                description="Failed to display alert.",
                color=0xff0000,
            )
            await self.discord_bot.send_message(message.channel.id, embed=error_embed)

    async def _handle_onboard_network(self, message):
        # Example: /onboard_network <node_name> <location> <type>
        parts = message.content.strip().split(maxsplit=3)
        if len(parts) < 3:
            await self.discord_bot.send_message(message.channel.id, "Usage: /onboard_network <node_name> <location> [type]")
            return
        node_name = parts[1]
        location = parts[2]
        node_type = parts[3] if len(parts) > 3 else "depot"
        try:
            embed = disnake.Embed(
                title="✅ Network Node Onboarded",
                description=f"Node **{node_name}** has been onboarded.",
                color=0x00ff00,
            )
            embed.add_field(name="Location", value=location, inline=True)
            embed.add_field(name="Type", value=node_type, inline=True)
            await self.discord_bot.send_message(message.channel.id, embed=embed)
        except (AttributeError, ValueError, TypeError, disnake.DiscordException, RuntimeError) as e:
            self.logger.error("Error onboarding network node: %s", e)
            error_embed = disnake.Embed(
                title=ERROR_TITLE,
                description="Failed to onboard network node.",
                color=0xff0000,
            )
            await self.discord_bot.send_message(message.channel.id, embed=error_embed)
            "PROD-001": Task(
                task_id="PROD-001",
                name="Produce 7.62mm Ammunition",
                task_type="production",
                status=TaskStatus.IN_PROGRESS,
                base_priority=2.5,
                created_at=datetime(
                    2024, 1, 15, 14, 30, tzinfo=UTC,
                ),
                metadata={
                    "target_quantity": 1000,
                    "current_progress": 650,
                    "facility": "Safe House Assembly",
                    "estimated_completion": "45 minutes",
                },
            ),
            "TRANS-001": Task(
                task_id="TRANS-001",
                name="Transport Supplies to Deadlands",
                task_type="transport",
                created_at=datetime(
                    2024, 1, 15, 13, 15, tzinfo=UTC,
                ),
                metadata={
                    "origin": "Westgate Depot",
                    "destination": "Reaching Trail Storage",
                    "cargo": "Mixed ammunition and medical supplies",
                    "blocker": (
                        "Route contested — waiting for frontline stabilization"
                    ),
                },
            ),
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
def create_bot(
    bot_auth_token: str,
    intents: disnake.Intents = DEFAULT_INTENTS,
) -> FoxholeBot:
    """Create and configure the Foxhole bot.

    Args:
        bot_auth_token: Discord bot token.
        intents: Discord Intents object (default: DEFAULT_INTENTS)

    Returns:
        Configured FoxholeBot instance.

    Raises:
        ValueError: If the token is not provided or invalid.
        TypeError: If the token is not a string.

    """
    # Define a common error message for token validation
    token_error_msg = "A valid Discord bot token must be provided."  # nosec: B105 # noqa: S105, E501, RUF100 # pylint: disable=line-too-long
    if not bot_auth_token:
        msg = token_error_msg
        raise ValueError(msg + " (None or empty)")
    if not isinstance(bot_auth_token, str):
        msg = token_error_msg
        raise TypeError(msg + f" (got {type(bot_auth_token)})")
    if len(bot_auth_token.strip()) == 0:
        msg = token_error_msg
        raise ValueError(msg + " (empty or whitespace)")

    # Disnake's bot.run(token) expects the token at runtime, not in the constructor. # noqa: E501, RUF100 # pylint: disable=line-too-long
    # We pass it to our constructor, which stores it for the run() call.
    return FoxholeBot(bot_token=bot_auth_token, intents=intents)


# Example usage
if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()

    env_bot_token = os.getenv("DISCORD_BOT_TOKEN")
    if not env_bot_token:
        MSG = "DISCORD_BOT_TOKEN environment variable not set."
        raise ValueError(MSG)

    # Use explicit intents
    bot = create_bot(env_bot_token, intents=DEFAULT_INTENTS)
    bot.run(env_bot_token)
