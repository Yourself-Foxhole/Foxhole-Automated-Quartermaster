#!/usr/bin/env python
"""
Main entry point for the Foxhole Logistics Discord Bot.
"""
import asyncio
import os
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv
from loguru import logger

from src.bot.cogs.command_handler import CommandHandler
from src.bot.cogs.task_manager import TaskManager
from src.bot.cogs.stock_manager import StockManager
from src.bot.cogs.location_manager import LocationManager
from src.bot.cogs.recipe_manager import RecipeManager
from src.bot.cogs.config_manager import ConfigManager
from src.bot.cogs.notification_engine import NotificationEngine
from src.bot.cogs.scheduler import Scheduler
from src.database.database_manager import DatabaseManager
from src.utils.logging import setup_logging


# Load environment variables
load_dotenv()

# Setup logging
setup_logging()


class FoxholeLogisticsBot(commands.Bot):
    """
    Main bot class for the Foxhole Logistics Discord Bot.
    """

    def __init__(self):
        # Initialize the bot with the command prefix from environment variables
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=os.getenv("DISCORD_PREFIX", "!"),
            intents=intents,
            help_command=None,  # Disable default help command
        )
        
        # Initialize managers
        self.db_manager = DatabaseManager()
        self.task_manager = TaskManager(self.db_manager)
        self.stock_manager = StockManager(self.db_manager)
        self.location_manager = LocationManager(self.db_manager)
        self.recipe_manager = RecipeManager(self.db_manager)
        self.config_manager = ConfigManager(self.db_manager)
        self.notification_engine = NotificationEngine()
        self.scheduler = Scheduler(self.task_manager, self.notification_engine)
        
        # Command handler
        self.command_handler = CommandHandler(
            self.task_manager,
            self.stock_manager,
            self.location_manager,
            self.recipe_manager,
            self.config_manager,
            self.notification_engine,
        )
    
    async def setup_hook(self):
        """
        Setup hook for the bot. Loads all cogs and initializes the database.
        """
        # Initialize database
        await self.db_manager.initialize()
        
        # Load cogs
        await self.add_cog(self.command_handler)
        await self.add_cog(self.task_manager)
        await self.add_cog(self.stock_manager)
        await self.add_cog(self.location_manager)
        await self.add_cog(self.recipe_manager)
        await self.add_cog(self.config_manager)
        await self.add_cog(self.notification_engine)
        await self.add_cog(self.scheduler)
        
        logger.info("Bot setup completed")
    
    async def on_ready(self):
        """
        Event handler for when the bot is ready.
        """
        logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Start the scheduler
        self.scheduler.start()
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="logistics operations"
            )
        )
    
    async def on_command_error(self, ctx, error):
        """
        Global error handler for command errors.
        """
        if isinstance(error, commands.CommandNotFound):
            # Ignore command not found errors
            return
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
            return
        
        # Log the error
        logger.error(f"Command error: {error}")
        
        # Send a generic error message
        await ctx.send("An error occurred while processing your command. Please try again later.")


async def main():
    """
    Main function to run the bot.
    """
    # Create the bot
    bot = FoxholeLogisticsBot()
    
    # Run the bot
    async with bot:
        await bot.start(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    asyncio.run(main()) 