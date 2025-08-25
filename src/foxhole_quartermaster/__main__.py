"""
Main entry point for the Foxhole Automated Quartermaster Discord bot.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .core.bot import TenantBot
from .utils.database import get_database_manager


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/bot.log') if Path('logs').exists() else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main application entry point."""
    # Verify required environment variables
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        logger.error("DISCORD_BOT_TOKEN environment variable is required")
        sys.exit(1)
    
    # Create bot instance
    command_prefix = os.getenv('BOT_COMMAND_PREFIX', '!')
    description = os.getenv('BOT_DESCRIPTION', 'Foxhole Automated Quartermaster - Multi-tenant logistics tracking bot')
    
    bot = TenantBot(
        command_prefix=command_prefix,
        description=description
    )
    
    # Load command modules
    try:
        await bot.load_extension('foxhole_quartermaster.commands.tenant')
        await bot.load_extension('foxhole_quartermaster.commands.logistics')
        logger.info("All command modules loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load command modules: {e}")
        sys.exit(1)
    
    # Start the bot
    try:
        logger.info("Starting Foxhole Automated Quartermaster bot...")
        async with bot:
            await bot.start(bot_token)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if bot.db_manager:
            await bot.db_manager.cleanup()
        logger.info("Bot shutdown complete")


if __name__ == '__main__':
    # Ensure logs directory exists
    Path('logs').mkdir(exist_ok=True)
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)