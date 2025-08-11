from unittest.mock import AsyncMock, MagicMock

import pytest

from data.discord.discord import DiscordChannelManager


@pytest.fixture
def channel_manager():
    client = MagicMock()
    return DiscordChannelManager(client=client)

@pytest.mark.asyncio
async def test_create_category(channel_manager):
    guild = AsyncMock()
    channel_manager.client.fetch_guild = AsyncMock(return_value=guild)
    guild.create_category_channel = AsyncMock(return_value="category")
    result = await channel_manager.create_category(123, "TestCat")
    assert result == "category"
    channel_manager.client.fetch_guild.assert_awaited_with(123)
    guild.create_category_channel.assert_awaited_with("TestCat")

@pytest.mark.asyncio
async def test_get_category(channel_manager):
    guild = AsyncMock()
    channel_manager.client.fetch_guild = AsyncMock(return_value=guild)
    guild.get_channel = MagicMock(return_value="category")
    result = await channel_manager.get_category(123, 456)
    assert result == "category"
    guild.get_channel.assert_called_with(456)

@pytest.mark.asyncio
async def test_update_category(channel_manager):
    category = AsyncMock()
    channel_manager.get_category = AsyncMock(return_value=category)
    category.edit = AsyncMock(return_value="updated")
    result = await channel_manager.update_category(1, 2, name="NewName")
    assert result == "updated"
    category.edit.assert_awaited_with(name="NewName")

@pytest.mark.asyncio
async def test_delete_category(channel_manager):
    category = AsyncMock()
    channel_manager.get_category = AsyncMock(return_value=category)
    category.delete = AsyncMock(return_value="deleted")
    result = await channel_manager.delete_category(1, 2)
    assert result == "deleted"
    category.delete.assert_awaited()

@pytest.mark.asyncio
async def test_create_text_channel(channel_manager):
    guild = AsyncMock()
    channel_manager.client.fetch_guild = AsyncMock(return_value=guild)
    guild.create_text_channel = AsyncMock(return_value="channel")
    result = await channel_manager.create_text_channel(1, "chan")
    assert result == "channel"
    guild.create_text_channel.assert_awaited_with("chan", category=None)

@pytest.mark.asyncio
async def test_get_channel(channel_manager):
    guild = AsyncMock()
    channel_manager.client.fetch_guild = AsyncMock(return_value=guild)
    guild.get_channel = MagicMock(return_value="chan")
    result = await channel_manager.get_channel(1, 2)
    assert result == "chan"
    guild.get_channel.assert_called_with(2)

@pytest.mark.asyncio
async def test_update_channel(channel_manager):
    channel = AsyncMock()
    channel_manager.get_channel = AsyncMock(return_value=channel)
    channel.edit = AsyncMock(return_value="updated")
    result = await channel_manager.update_channel(1, 2, name="new")
    assert result == "updated"
    channel.edit.assert_awaited_with(name="new")

@pytest.mark.asyncio
async def test_delete_channel(channel_manager):
    channel = AsyncMock()
    channel_manager.get_channel = AsyncMock(return_value=channel)
    channel.delete = AsyncMock(return_value="deleted")
    result = await channel_manager.delete_channel(1, 2)
    assert result == "deleted"
    channel.delete.assert_awaited()

@pytest.mark.asyncio
async def test_create_thread(channel_manager):
    channel = AsyncMock()
    channel_manager.client.fetch_channel = AsyncMock(return_value=channel)
    channel.create_thread = AsyncMock(return_value="thread")
    result = await channel_manager.create_thread(2, "t")
    assert result == "thread"
    channel.create_thread.assert_awaited_with(name="t", auto_archive_duration=60)

@pytest.mark.asyncio
async def test_create_thread_from_message(channel_manager):
    channel = AsyncMock()
    message = AsyncMock()
    channel_manager.client.fetch_channel = AsyncMock(return_value=channel)
    channel.fetch_message = AsyncMock(return_value=message)
    message.create_thread = AsyncMock(return_value="thread")
    result = await channel_manager.create_thread(2, "t", message_id=3)
    assert result == "thread"
    channel.fetch_message.assert_awaited_with(3)
    message.create_thread.assert_awaited_with(name="t", auto_archive_duration=60)

@pytest.mark.asyncio
async def test_get_thread(channel_manager):
    channel = AsyncMock()
    channel_manager.client.fetch_channel = AsyncMock(return_value=channel)
    channel.get_thread = MagicMock(return_value="thread")
    result = await channel_manager.get_thread(2, 3)
    assert result == "thread"
    channel.get_thread.assert_called_with(3)

@pytest.mark.asyncio
async def test_update_thread(channel_manager):
    thread = AsyncMock()
    channel_manager.get_thread = AsyncMock(return_value=thread)
    thread.edit = AsyncMock(return_value="updated")
    result = await channel_manager.update_thread(2, 3, name="new")
    assert result == "updated"
    thread.edit.assert_awaited_with(name="new")

@pytest.mark.asyncio
async def test_delete_thread(channel_manager):
    thread = AsyncMock()
    channel_manager.get_thread = AsyncMock(return_value=thread)
    thread.delete = AsyncMock(return_value="deleted")
    result = await channel_manager.delete_thread(2, 3)
    assert result == "deleted"
    thread.delete.assert_awaited()
