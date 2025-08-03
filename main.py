# This is the entry point to our application
# This contains the main event loop
# The only job of this file is to start the layers of our application and handle any command line parameters

import asyncio
from data.discord.discord import DiscordBot


def main() -> None:
    # Example: Replace 'YOUR_TOKEN' with your actual Discord bot token
    token = 'YOUR_TOKEN'
    bot = DiscordBot(token=token)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_in_executor(None, bot.run)
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        bot.shutdown()
        loop.close()

if __name__ == '__main__':
    main()