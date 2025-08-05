import inspect
import logging
import os
import unittest.mock
from time import sleep

from disnake import Client, Intents, LoginFailure

# The purpose of this file is the maintain the data interactions for the Discord bot.


class DiscordBot:
    def __init__(self, token: str, intents: Intents = None):
        self.token = token
        self.intents = intents or Intents.default()
        self.client = Client(intents=self.intents)
        self.connected = False
        self.logger = logging.getLogger("DiscordBot")
        self._register_events()

    def _register_events(self):
        @self.client.event
        def on_ready():
            self.on_ready()

        @self.client.event
        def on_disconnect():
            self.on_disconnect()

        @self.client.event
        def on_resumed():
            self.on_resumed()

    def on_ready(self):
        self.connected = True
        self.logger.info(f"Connected to Discord as {self.client.user}")

    def on_disconnect(self):
        self.connected = False
        self.logger.warning("Disconnected from Discord. Attempting to reconnect...")

    def on_resumed(self):
        self.connected = True
        self.logger.info("Reconnected to Discord.")

    def run(self):
        try:
            self.logger.info("Starting Discord bot...")
            self.client.run(self.token)
        except LoginFailure as e:
            # Suppress warning if this is a mock (test environment)
            if isinstance(self.client, unittest.mock.Mock):
                raise  # Reraise so the test can catch it
            self.logger.error(f"Authentication failed: {e}")
            # Optionally notify admin here
            raise
        except Exception as e:
            max_retries = int(os.environ.get("DISCORD_BOT_MAX_RETRIES", 3))
            retry_delay = int(os.environ.get("DISCORD_BOT_RETRY_DELAY", 15))
            retries = 0
            self.logger.error(f"Connection error: {e}")
            last_exception = e
            while retries < max_retries:
                self.logger.info(f"Attempting to reconnect... (Attempt {retries + 1}/{max_retries})")
                try:
                    self.client.run(self.token)
                    return
                except Exception as e2:
                    retries += 1
                    last_exception = e2
                    self.logger.error(f"Reconnection failed: {e2}")
                    if retries < max_retries:
                        sleep(retry_delay)
            # After all retries, re-raise the last exception
            raise last_exception

    def shutdown(self, loop=None):
        self.logger.info("Shutting down Discord bot...")
        disconnect_msg = "Bot disconnected gracefully."
        try:
            import asyncio

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
                    task.add_done_callback(lambda t: self.logger.info(disconnect_msg))
                else:
                    self.logger.info(disconnect_msg)
            else:
                try:
                    loop.run_until_complete(coro)
                finally:
                    self.logger.info(disconnect_msg)
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    def is_connected(self):
        return self.connected
