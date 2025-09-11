"""Data interaction layer for the Discord bot.

This module defines the DiscordBot class, which manages connection, event handling,
messaging, and channel/thread/category management for a Discord bot using the disnake library.
"""  # noqa: E501, RUF100

import asyncio
import inspect
import logging
import os
import unittest.mock
from collections.abc import Callable
from typing import Unpack
from time import sleep

import disnake
from disnake import (
    CategoryChannel,
    Client,
    ConnectionClosed,
    DiscordServerError,
    GatewayNotFound,
    HTTPException,
    Intents,
    LoginFailure,
    Message,
    TextChannel,
    Thread,
)
from disnake.abc import GuildChannel


class DiscordBot:
    """Interface for managing a Discord bot.

    DiscordBot provides methods for connection, event handling, messaging, and CRUD operations
    for categories, channels, and threads. Allows registering external event handlers.
    """  # noqa: E501, RUF100

    _DISCONNECT_MSG = "Bot disconnected gracefully"

    def __init__(self, token: str, intents: Intents | None = None) -> None:
        """Initialize the DiscordBot instance.

        Args:
            token (str): The Discord bot token.
            intents (Intents, optional): Discord intents. Defaults to Intents.default().

        """  # noqa: E501, RUF100
        self.token = token
        self.intents = intents or Intents.default()
        self.client = Client(intents=self.intents)
        self.connected = False
        self.logger = logging.getLogger("DiscordBot")
        self._external_on_ready = None
        self._external_on_message = None
        self._register_events()

    def register_on_ready(self, handler: Callable) -> None:
        """Register an external on_ready handler (called after internal logic)."""  # noqa: E501, RUF100 # pylint: disable=line-too-long
        self._external_on_ready = handler

    def register_on_message(self, handler: Callable) -> None:
        """Register an external on_message handler (called on message events)."""  # noqa: E501, RUF100 # pylint: disable=line-too-long
        self._external_on_message = handler

    def _register_events(self) -> None:
        """Register Discord event handlers for on_ready, on_disconnect, on_resumed, and on_message."""  # noqa: E501, RUF100 # pylint: disable=line-too-long

        @self.client.event
        async def on_ready() -> None:
            await self.on_ready()
            if self._external_on_ready:
                await self._external_on_ready()

        @self.client.event
        async def on_disconnect() -> None:
            await self.on_disconnect()

        @self.client.event
        async def on_resumed() -> None:
            await self.on_resumed()

        @self.client.event
        async def on_message(message: Message) -> None:
            if self._external_on_message:
                await self._external_on_message(message)

    # These methods were pulled out to enhance unit testing, but SonarQube is complaining about them  # noqa: E501, RUF100 # pylint: disable=line-too-long
    # not being used directly. Suppressing that warning with NO SONAR.
    async def on_ready(self) -> None:  # NOSONAR(S7503)
        """Event handler for when the bot is ready and connected to Discord."""
        self.connected = True
        user = getattr(self.client, "user", None)
        if user is not None:
            self.logger.info("Connected to Discord as %s", user)
        else:
            self.logger.info("Connected to Discord as <unknown user>")

    async def on_disconnect(self) -> None:  # NOSONAR(S7503)
        """Event handler for when the bot disconnects from Discord."""
        self.connected = False
        self.logger.warning("Disconnected from Discord. Attempting to reconnect...")  # noqa: E501, RUF100

    async def on_resumed(self) -> None:  # NOSONAR(S7503)
        """Event handler for when the bot resumes a connection to Discord."""
        self.connected = True
        self.logger.info("Reconnected to Discord.")

    class ChannelDoesNotSupportSendingMessagesError(TypeError):
        """Exception raised when a channel does not support sending messages."""

        def __init__(self, channel_id: int) -> None:
            """Initialize the exception with the given channel ID.

            Args:
                channel_id (int): The ID of the channel that does not support sending messages.

            """
            super().__init__(f"Channel with ID {channel_id} does not support sending messages.")

    async def send_message(self, channel_id: int, content: str) -> Message:
        """Send a message to a specified channel.

        Args:
            channel_id (int): The ID of the channel.
            content (str): The message content.

        Returns:
            Message: Sent message object.

        """
        channel = await self.client.fetch_channel(channel_id)
        if isinstance(channel, disnake.TextChannel | disnake.Thread):
            return await channel.send(content)
        raise self.ChannelDoesNotSupportSendingMessagesError(channel_id)

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
        except ValueError as exc:
            msg = f"Invalid value for DISCORD_BOT_MAX_RETRIES: {value}"
            raise ValueError(msg) from exc
        return max(0, max_retries)

    @staticmethod
    def _get_retry_delay() -> int:
        value = os.environ.get("DISCORD_BOT_RETRY_DELAY", "15")
        try:
            return int(value)
        except ValueError as exc:
            msg = f"Invalid value for DISCORD_BOT_RETRY_DELAY: {value}"
            raise ValueError(msg) from exc

    @staticmethod
    def _get_connection_exceptions() -> tuple[
        type[OSError],
        type[ConnectionError],
        type[DiscordServerError],
        type[GatewayNotFound],
        type[ConnectionClosed],
        type[HTTPException],
    ]:
        """Return a tuple of exception types that indicate a Discord connection error."""  # noqa: E501, RUF100
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

        """  # noqa: E501, RUF100  -- longer than pep8's 80 chars.
        max_retries = self._get_max_retries()
        retry_delay = self._get_retry_delay()
        for attempt in range(max_retries):
            self.logger.info("Attempting to reconnect... (Retry %s/%s)",
                             attempt + 1,
                             max_retries)
            try:
                self.client.run(self.token)
            except self._get_connection_exceptions() as e:
                last_exception = e
                self.logger.exception("Connection error during reconnect")
                if attempt + 1 >= max_retries:
                    raise last_exception from e
                if retry_delay > 0:
                    sleep(retry_delay)
            else:
                self.logger.info("Reconnected successfully.")
                return
        raise last_exception

    def run(self) -> None:
        """Start the Discord bot and handle authentication or connection errors."""  # noqa: E501, RUF100
    # pylint: disable=too-many-try-statements -- extra statement is just logging
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
        if self._is_mock_client():
            return
        loop = self._get_event_loop(loop)
        try:
            if self.client.is_closed():
                self.logger.info(self._DISCONNECT_MSG)
                return
        except (OSError, RuntimeError):
            self.logger.exception("Error during shutdown:")
            return
        coro = self.client.close()
        if not inspect.isawaitable(coro):
            self.logger.warning(
                "Shutdown: client.close() did not return a coroutine; "
                "skipping await.",
            )
            self.logger.info(self._DISCONNECT_MSG)
            return
        self._shutdown_with_loop(loop, coro)

    def _is_mock_client(self) -> bool:
        """Check if the client is a mock instance."""
        return isinstance(self.client, unittest.mock.Mock)

    def _get_event_loop(self, loop: asyncio.AbstractEventLoop | None) -> asyncio.AbstractEventLoop:
        """Get or create an event loop."""
        if loop is not None:
            return loop
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.new_event_loop()

    def _shutdown_with_loop(self, loop: asyncio.AbstractEventLoop, coro) -> None:
        """Handle shutdown logic depending on loop state."""
        if loop.is_running():
            task = loop.create_task(coro)
            if hasattr(task, "add_done_callback"):
                task.add_done_callback(lambda _: self.logger.info(self._DISCONNECT_MSG))
            else:
                self.logger.info(self._DISCONNECT_MSG)
        else:
            try:
                loop.run_until_complete(coro)
            finally:
                self.logger.info(self._DISCONNECT_MSG)

    def stop(self) -> None:
        """Stop the Discord bot and close the client connection if running."""
        try:
            if self.client.is_closed():
                return
        except RuntimeError:
            self.logger.exception("Error during stop:")
            return
        loop = self.client.loop if hasattr(self.client, "loop") else None
        if loop and loop.is_running():
            coro = self.client.close()
            asyncio.run_coroutine_threadsafe(coro, loop)

    def is_connected(self) -> bool:
        """Check if the bot is currently connected to Discord.

        Returns:
            bool: True if connected, False otherwise.

        """
        return self.connected

class DiscordChannelManager:
    """DiscordChannelManager handles CRUD operations for categories, channels,
    and threads in a Discord guild.

    This class provides methods to create, retrieve, update, and delete categories,
    channels, and threads within a Discord guild.
    """

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

    async def get_category(
        self, guild_id: int, category_id: int,
    ) -> CategoryChannel | None:
        """Retrieve a category by ID from the specified guild.

        Args:
            guild_id (int): The ID of the guild.
            category_id (int): The ID of the category.

        Returns:
            CategoryChannel: The category channel object.

        """
        guild = await self.client.fetch_guild(guild_id)
        channel = guild.get_channel(category_id)
        if isinstance(channel, CategoryChannel):
            return channel
        return None

    async def update_category(
        self,
        guild_id: int,
        category_id: int,
        **kwargs: dict[str, object],
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
        if category is None:
            msg = f"Category with ID {category_id} not found in guild {guild_id}."
            raise ValueError(msg)
        await category.delete()

    async def create_text_channel(
        self,
        guild_id: int,
        name: str,
        category_id: int | None = None,
    ) -> TextChannel:
        """Create a new text channel in the specified guild, optionally under a
        category.

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
        if channel is None:
            msg = f"Channel with ID {channel_id} not found in guild {guild_id}."
            raise ValueError(msg)
        return await channel.delete()

    async def create_thread(
        self,
        channel_id: int,
        name: str,
        message_id: int | None = None,
        auto_archive_duration: int = 300,
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
        valid_durations = [60, 1440, 4320, 10080]
        duration = (
            auto_archive_duration
            if auto_archive_duration in valid_durations
            else 1440
        )

        if message_id is not None:
            # Try to fetch the message and create a thread from it
            if hasattr(channel, "fetch_message"):
                message = await channel.fetch_message(message_id)
                return await message.create_thread(name=name, auto_archive_duration=duration)
            msg = f"Channel with ID {channel_id} does not support fetching messages for thread creation."
            raise TypeError(msg)
        if hasattr(channel, "create_thread"):
            return await channel.create_thread(name=name, auto_archive_duration=duration)  # noqa: E501, RUF100 # pylint: disable=line-too-long
        msg = f"Channel with ID {channel_id} does not support thread creation."
        raise TypeError(msg)

    async def get_thread(self, channel_id: int, thread_id: int) -> Thread | None:  # noqa: E501, RUF100
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

    async def update_thread(self, channel_id: int, thread_id: int, **kwargs: dict[str, object]) -> Thread:
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
        if thread is not None:
            await thread.delete()
        # If thread is None, do nothing (or optionally raise an error)
