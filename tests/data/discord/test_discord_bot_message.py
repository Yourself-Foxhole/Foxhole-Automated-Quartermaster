from unittest import mock

import pytest

from data.discord.discord import DiscordBot


@pytest.mark.asyncio
async def test_send_message_posts_content():
    bot = DiscordBot(token="dummy")
    bot.client = mock.AsyncMock()
    mock_channel = mock.AsyncMock()
    bot.client.fetch_channel.return_value = mock_channel
    mock_channel.send.return_value = "sent-message"
    result = await bot.send_message(12345, "Hello!")
    bot.client.fetch_channel.assert_awaited_once_with(12345)
    mock_channel.send.assert_awaited_once_with("Hello!")
    assert result == "sent-message"

@pytest.mark.asyncio
async def test_add_reaction_adds_emoji():
    bot = DiscordBot(token="dummy")
    mock_message = mock.AsyncMock()
    await bot.add_reaction(mock_message, "👍")
    mock_message.add_reaction.assert_awaited_once_with("👍")

