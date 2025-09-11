# This is the entry point to our application
# This contains the main event loop
# The only job of this file is to start the layers of our application and handle any command line parameters

import os

from dotenv import load_dotenv

from data_pipeline.bot import create_bot

load_dotenv()


def main() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set.")
    bot = create_bot(token)
    bot.run(token)


if __name__ == "__main__":
    main()
