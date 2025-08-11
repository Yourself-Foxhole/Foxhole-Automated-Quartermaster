import asyncio
import os
import threading

import pytest
import pytest_asyncio

from data.discord.discord import DiscordBot

pytest_mark_async = pytest.mark.asyncio

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_TEST_CHANNEL_ID")
TEST_EMOJI = os.getenv("DISCORD_TEST_EMOJI", "👍")


@pytest.mark.skipif(not DISCORD_TOKEN or not CHANNEL_ID, reason="Discord integration environment not configured.")
@pytest_asyncio.fixture
async def discord_bot():
    bot = DiscordBot(token=DISCORD_TOKEN)
    ready_event = threading.Event()

    # This is an event hook that will be called when the bot is ready. It's okay if unused args/kwargs are present.
    async def on_ready_override():
        try:
            await bot.on_ready()
        finally:
            ready_event.set()

    bot.client.event(on_ready_override)

    def run_bot():
        # noinspection PyBroadException
        # Broad exception in test okay
        try:
            bot.client.run(DISCORD_TOKEN)
        except Exception:
            # Log or handle exceptions from the bot thread if needed
            pass

    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    loop = asyncio.get_event_loop()
    # noinspection PyTypeChecker,PyArgumentList,PydanticTypeChecker
    # This is a false positive, the linter doesn't understand the type here
    # Not going to add extra complexity to silence it
    await loop.run_in_executor(None, ready_event.wait)
    try:
        yield bot
    finally:
        bot.stop()
        thread.join(timeout=5)


@pytest.mark.asyncio
async def test_send_message_and_add_reaction_integration(discord_bot):
    message = await discord_bot.send_message(int(CHANNEL_ID), "Integration test message!")
    assert hasattr(message, "id"), "Message was not sent successfully."
    await discord_bot.add_reaction(message, TEST_EMOJI)
    # Optionally, fetch the message and check reaction
    fetched_message = await discord_bot.client.get_channel(int(CHANNEL_ID)).fetch_message(message.id)
    reactions = [str(r.emoji) for r in fetched_message.reactions]
    assert TEST_EMOJI in reactions, f"Reaction {TEST_EMOJI} not found on message."
    # Clean up: delete the test message
    await message.delete()
