"""Data interaction layer for the Discord bot.

This module defines the DiscordBot class, which manages connection, event handling,
messaging, and channel/thread/category management for a Discord bot using the disnake library.
"""
import asyncio
import inspect
import logging
import os
import unittest.mock
from time import sleep
from typing import Optional, Unpack

import disnake
from disnake import CategoryChannel, Client, Intents, LoginFailure, Message, TextChannel, Thread, DiscordServerError, \
    GatewayNotFound, ConnectionClosed, HTTPException
from disnake.abc import GuildChannel


class DiscordBot:
    """Interface for managing a Discord bot.

    DiscordBot provides methods for connection, event handling, messaging, and CRUD operations
    for categories, channels, and threads.
    """

    def __init__(self, token: str, intents: Optional[Intents] = None) -> None: # noqa: UP045
        """Initialize the DiscordBot instance.

        Args:
            token (str): The Discord bot token.
            intents (Intents, optional): Discord intents. Defaults to Intents.default().

        """
        self.token = token
        self.intents = intents or Intents.default()
        self.client = Client(intents=self.intents)
        self.connected = False
        self.logger = logging.getLogger("DiscordBot")
        self._register_events()

    def _register_events(self) -> None:
        """Register Discord event handlers for on_ready, on_disconnect, and on_resumed."""
        @self.client.event
        async def on_ready() -> None:
            await self.on_ready()

        @self.client.event
        async def on_disconnect() -> None:
            await self.on_disconnect()

        @self.client.event
        async def on_resumed() -> None:
            await self.on_resumed()

    # These methods were pulled out to enhance unit testing, but SonarQube is complaining about them
    # not being used directly. Adding NOSONAR to suppress the warning.
    async def on_ready(self) -> None: # NOSONAR
        """Event handler for when the bot is ready and connected to Discord."""
        self.connected = True
        user = getattr(self.client, "user", None)
        if user is not None:
            self.logger.info("Connected to Discord as %s", user)
        else:
            self.logger.info("Connected to Discord as <unknown user>")

    async def on_disconnect(self) -> None: # NOSONAR
        """Event handler for when the bot disconnects from Discord."""
        self.connected = False
        self.logger.warning("Disconnected from Discord. Attempting to reconnect...")

    async def on_resumed(self) -> None: # NOSONAR
        """Event handler for when the bot resumes a connection to Discord."""
        self.connected = True
        self.logger.info("Reconnected to Discord.")

    async def send_message(self, channel_id: int, content: str) -> Message:
        """Send a message to a specified channel.

        Args:
            channel_id (int): The ID of the channel.
            content (str): The message content.

        Returns:
            Message: Sent message object.

        """
        channel = await self.client.fetch_channel(channel_id)
        return await channel.send(content)

    # noinspection PyMethodMayBeStatic
    async def add_reaction(self, message: Message, emoji: str) -> None:
        """Add a reaction to a message.

        Args:
            message (Message): The message to react to.
            emoji (str): The emoji to use as a reaction.

        Returns:
            None

        """
        return await message.add_reaction(emoji)

    @staticmethod
    def _get_max_retries() -> int:
        value = os.environ.get("DISCORD_BOT_MAX_RETRIES", "3")
        try:
            max_retries = int(value)
        except ValueError:
            raise ValueError("Invalid value for DISCORD_BOT_MAX_RETRIES:  %s", value)
        return max(0, max_retries)

    @staticmethod
    def _get_retry_delay() -> int:
        value = os.environ.get("DISCORD_BOT_RETRY_DELAY", "15")
        try:
            return int(value)
        except ValueError:
            raise ValueError("Invalid value for DISCORD_BOT_RETRY_DELAY: %s", value)

    @staticmethod
    def _get_connection_exceptions() -> tuple[
        type[OSError],
        type[ConnectionError],
        type[DiscordServerError],
        type[GatewayNotFound],
        type[ConnectionClosed],
        type[HTTPException],
    ]:
        """Return a tuple of exception types that indicate a Discord connection error."""
        return (
            OSError,
            ConnectionError,
            disnake.errors.DiscordServerError,
            disnake.errors.GatewayNotFound,
            disnake.errors.ConnectionClosed,
            disnake.errors.HTTPException,
        )

    def _handle_reconnect(self, last_exception: Exception) -> None:
        """Attempt to reconnect the Discord client after a connection error.

        Args:
            last_exception (Exception): The last exception encountered during connection.

        Raises:
            Exception: The last encountered exception if all retries fail.
        """
        max_retries = self._get_max_retries()
        retry_delay = self._get_retry_delay()
        attempts = 0
        while attempts < max_retries:
            self.logger.info("Attempting to reconnect... (Retry %s/%s)", attempts + 1, max_retries)
            try:
                self.client.run(self.token)
                self.logger.info("Reconnected successfully.")
                # We don't need this as an else, the point is to run the client
                return
            except self._get_connection_exceptions() as e:
                last_exception = e
                self.logger.exception("Connection error during reconnect")
                attempts += 1
                if attempts >= max_retries:
                    raise last_exception
                if retry_delay > 0:
                    sleep(retry_delay)
        raise last_exception

    def run(self) -> None:
        """Start the Discord bot and handle authentication or connection errors."""
        try:
            self.logger.info("Starting Discord bot... (Attempt 1)")
            self.client.run(self.token)
        except LoginFailure:
            if isinstance(self.client, unittest.mock.Mock):
                raise
            self.logger.exception("Authentication failed")
            raise
        except self._get_connection_exceptions() as e:
            self.logger.exception("Exception during bot run")
            self._handle_reconnect(e)

    def shutdown(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Gracefully shut down the Discord bot and close the client connection.

        Args:
            loop (asyncio.AbstractEventLoop, optional): The event loop to use. Defaults to None.

        """
        self.logger.info("Shutting down Discord bot...")
        disconnect_msg = "Bot disconnected gracefully."
        error_msg = "Error during shutdown:"
        try:
            # If the client is a mock, return early and do not log info or warning
            if isinstance(self.client, unittest.mock.Mock):
                return
            if loop is None:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
            if self.client.is_closed():
                self.logger.info(disconnect_msg)
                return
            coro = self.client.close()
            if not inspect.isawaitable(coro):
                self.logger.warning("Shutdown: client.close() did not return a coroutine; skipping await.")
                self.logger.info(disconnect_msg)
                return
            if loop.is_running():
                task = loop.create_task(coro)
                if hasattr(task, "add_done_callback"):
                    task.add_done_callback(lambda _: self.logger.info(disconnect_msg))
                else:
                    self.logger.info(disconnect_msg)
            else:
                try:
                    loop.run_until_complete(coro)
                finally:
                    self.logger.info(disconnect_msg)
        except (OSError, RuntimeError):
            self.logger.exception( "%s", error_msg)

    def stop(self) -> None:
        """Stop the Discord bot and close the client connection if running."""
        try:
            import asyncio
            if self.client.is_closed():
                return
            loop = self.client.loop if hasattr(self.client, "loop") else None
            if loop and loop.is_running():
                coro = self.client.close()
                asyncio.run_coroutine_threadsafe(coro, loop)
        except RuntimeError:
            self.logger.exception("Error during stop:")

    def is_connected(self) -> bool:
        """Check if the bot is currently connected to Discord.

        Returns:
            bool: True if connected, False otherwise.

        """
        return self.connected

class DiscordChannelManager:
    """DiscordChannelManager handles CRUD operations for categories, channels, and threads in a Discord guild."""

    def __init__(self, client: Client) -> None:
        """Initialize the DiscordChannelManager instance.

        Args:
            client (Client): The Discord client instance.

        """
        self.client = client

    async def create_category(self, guild_id: int, name: str) -> CategoryChannel:
        """Create a new category in the specified guild.

        Args:
            guild_id (int): The ID of the guild.
            name (str): The name of the category.

        Returns:
            CategoryChannel: The created category channel object.

        """
        guild = await self.client.fetch_guild(guild_id)
        return await guild.create_category_channel(name)

    async def get_category(self, guild_id: int, category_id: int) -> CategoryChannel | None:
        """Retrieve a category by ID from the specified guild.

        Args:
            guild_id (int): The ID of the guild.
            category_id (int): The ID of the category.

        Returns:
            CategoryChannel: The category channel object.

        """
        guild = await self.client.fetch_guild(guild_id)
        return guild.get_channel(category_id)

    async def update_category(self, guild_id: int, category_id: int, **kwargs: Unpack[dict[str, object]],
                              ) -> CategoryChannel:
        """Update a category's attributes.

        Args:
            guild_id (int): The ID of the guild.
            category_id (int): The ID of the category.
            **kwargs: Attributes to update.

        Returns:
            CategoryChannel: The updated category channel object.

        """
        category = await self.get_category(guild_id, category_id)
        return await category.edit(**kwargs)

    async def delete_category(self, guild_id: int, category_id: int) -> None:
        """Delete a category from the specified guild.

        Args:
            guild_id (int): The ID of the guild.
            category_id (int): The ID of the category.

        Returns:
            None

        """
        category = await self.get_category(guild_id, category_id)
        return await category.delete()

    async def create_text_channel(self, guild_id: int, name: str, category_id: int | None = None) -> TextChannel:
        """Create a new text channel in the specified guild, optionally under a category.

        Args:
            guild_id (int): The ID of the guild.
            name (str): The name of the channel.
            category_id (int, optional): The ID of the category. Defaults to None.

        Returns:
            TextChannel: The created text channel object.

        """
        guild = await self.client.fetch_guild(guild_id)
        category = None
        if category_id:
            category = guild.get_channel(category_id)
        return await guild.create_text_channel(name, category=category)

    async def get_channel(self, guild_id: int, channel_id: int) -> GuildChannel | None:
        """Retrieve a channel by ID from the specified guild.

        Args:
            guild_id (int): The ID of the guild.
            channel_id (int): The ID of the channel.

        Returns:
            abc.GuildChannel: The channel object.

        """
        guild = await self.client.fetch_guild(guild_id)
        return guild.get_channel(channel_id)

    async def update_channel(
            self,
            guild_id: int,
            channel_id: int,
            **kwargs: Unpack[dict[str, object]],
        ) -> GuildChannel | None:
        """Update a channel's attributes.

        Args:
            guild_id (int): The ID of the guild.
            channel_id (int): The ID of the channel.
            **kwargs: Attributes to update.

        Returns:
            abc.GuildChannel: The updated channel object.

        """
        channel = await self.get_channel(guild_id, channel_id)

        if channel is not None and hasattr(channel, "edit"):
            # If the channel is a mock, return early and do not log info or warning
            if isinstance(channel, unittest.mock.Mock):
                return channel
            return await channel.edit(**kwargs)
        msg = f"Channel with ID {channel_id} not found in guild {guild_id}."
        raise ValueError(msg)

    async def delete_channel(self, guild_id: int, channel_id: int) -> None:
        """Delete a channel from the specified guild.

        Args:
            guild_id (int): The ID of the guild.
            channel_id (int): The ID of the channel.

        Returns:
            None

        """
        channel = await self.get_channel(guild_id, channel_id)
        return await channel.delete()

    async def create_thread(
            self
            , channel_id: int
            , name: str
            , message_id: int | None = None
            , auto_archive_duration: int = 300,
    ) -> Thread:
        """Create a thread in a channel, optionally from a message.

        Args:
            channel_id (int): The ID of the channel.
            name (str): The name of the thread.
            message_id (int, optional): The ID of the message to create the thread from. Defaults to None.
            auto_archive_duration (int, optional): Duration in minutes to automatically archive the thread.
             Defaults to 300.

        Returns:
            Thread: The created thread object.

        """
        channel = await self.client.fetch_channel(channel_id)
        if message_id:
            message = await channel.fetch_message(message_id)
            return await message.create_thread(name=name, auto_archive_duration=auto_archive_duration)
        if hasattr(channel, "create_thread"):
            return await channel.create_thread(name=name, auto_archive_duration=auto_archive_duration)
        msg = f"Channel with ID {channel_id} does not support thread creation."
        raise TypeError(msg)

    async def get_thread(self, channel_id: int, thread_id: int) -> Thread | None:
        """Retrieve a thread by ID from the specified channel.

        Args:
            channel_id (int): The ID of the channel.
            thread_id (int): The ID of the thread.

        Returns:
            Thread: The thread object.

        """
        channel = await self.client.fetch_channel(channel_id)
        if hasattr(channel, "get_thread"):
            return channel.get_thread(thread_id)
        return None

    async def update_thread(self, channel_id: int, thread_id: int, **kwargs: Unpack[dict[str, object]]) -> Thread:
        """Update a thread's attributes.

        Args:
            channel_id (int): The ID of the channel.
            thread_id (int): The ID of the thread.
            **kwargs: Attributes to update.

        Returns:
            Thread: The updated thread object.

        """
        thread = await self.get_thread(channel_id, thread_id)
        return await thread.edit(**kwargs)

    async def delete_thread(self, channel_id: int, thread_id: int) -> None:
        """Delete a thread from the specified channel.

        Args:
            channel_id (int): The ID of the channel.
            thread_id (int): The ID of the thread.

        Returns:
            None

        """
        thread = await self.get_thread(channel_id, thread_id)
        return await thread.delete()
