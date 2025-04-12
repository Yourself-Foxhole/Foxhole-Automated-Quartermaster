"""
Main application module for the Logistics Task Board.

This module initializes and runs the Discord bot and task service.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

from src.database.database_manager import DatabaseManager
from src.services.task_service import TaskService
from src.services.discord_service import DiscordService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log")
    ]
)

logger = logging.getLogger(__name__)

async def check_auto_release_task(task_service: TaskService):
    """Background task to check for tasks that need to be auto-released."""
    while True:
        try:
            auto_released_tasks = await task_service.check_auto_release()
            if auto_released_tasks:
                logger.info(f"Auto-released {len(auto_released_tasks)} tasks due to inactivity")
        except Exception as e:
            logger.error(f"Error in auto-release task: {e}")
        
        # Check every 5 minutes
        await asyncio.sleep(300)

async def main():
    """Main application entry point."""
    # Load environment variables
    load_dotenv()
    
    # Initialize database
    database_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///logistics.db")
    database_manager = DatabaseManager(database_url)
    await database_manager.initialize()
    
    # Initialize services
    task_service = TaskService(database_manager)
    discord_service = DiscordService(task_service)
    
    # Start auto-release background task
    auto_release_task = asyncio.create_task(check_auto_release_task(task_service))
    
    try:
        # Start Discord bot
        logger.info("Starting Discord bot...")
        await discord_service.start()
    except Exception as e:
        logger.error(f"Error starting Discord bot: {e}")
    finally:
        # Clean up
        auto_release_task.cancel()
        await discord_service.stop()
        await database_manager.close()

if __name__ == "__main__":
    asyncio.run(main()) 