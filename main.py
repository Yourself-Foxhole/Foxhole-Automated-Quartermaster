# This is the entry point to our application
# This contains the main event loop
# The only job of this file is to start the layers of our application and handle any command line parameters

import asyncio
import os

from dotenv import load_dotenv

from data.discord.discord import DiscordBot

load_dotenv()


def main() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set.")
    bot = DiscordBot(token=token)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # noinspection PyTypeChecker, PyArgumentList, PyUnresolvedReferences, PydanticTypeChecker
        # This is a false positive, the linter doesn't understand the type here
        loop.run_until_complete(loop.run_in_executor(None, lambda: bot.run()))
    finally:
        loop.close()


if __name__ == "__main__":
    main()
