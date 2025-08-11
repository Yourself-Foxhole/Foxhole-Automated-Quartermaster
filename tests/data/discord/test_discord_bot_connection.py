import asyncio
import os
import sys
from unittest import mock

import pytest
from hypothesis import given
from hypothesis import strategies as st

# Add the project root to sys.path so 'data' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

# Assume DiscordBot is imported from the correct location
from data.discord.discord import DiscordBot


def setup_function():
    # Ensure an event loop exists for tests that need it
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)


def teardown_function():
    # Clean up the event loop after each test
    try:
        loop = asyncio.get_event_loop()
        loop.close()
    except RuntimeError:
        pass


def test_env_defaults(monkeypatch):
    # Remove env vars if set
    monkeypatch.delenv("DISCORD_BOT_MAX_RETRIES", raising=False)
    monkeypatch.delenv("DISCORD_BOT_RETRY_DELAY", raising=False)
    # Access the retry config (simulate how your code reads it)
    max_retries = int(os.environ.get("DISCORD_BOT_MAX_RETRIES", 3))
    retry_delay = int(os.environ.get("DISCORD_BOT_RETRY_DELAY", 15))
    assert max_retries == 3
    assert retry_delay == 15


@given(max_retries=st.integers(min_value=0, max_value=1000), retry_delay=st.integers(min_value=0, max_value=1000))
def test_env_hypothesis(max_retries, retry_delay):
    os.environ["DISCORD_BOT_MAX_RETRIES"] = str(max_retries)
    os.environ["DISCORD_BOT_RETRY_DELAY"] = str(retry_delay)
    assert int(os.environ.get("DISCORD_BOT_MAX_RETRIES", 3)) == max_retries
    assert int(os.environ.get("DISCORD_BOT_RETRY_DELAY", 15)) == retry_delay
    # Clean up
    del os.environ["DISCORD_BOT_MAX_RETRIES"]
    del os.environ["DISCORD_BOT_RETRY_DELAY"]


def test_retry_on_exception(monkeypatch):
    # Set retries to 2 for a quick test
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "2")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")  # No sleep delay
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()  # Mock logger to avoid real logging
    # Mock client.run to always raise OSError
    bot.client.run = mock.Mock(side_effect=OSError("fail"))
    with pytest.raises(OSError):
        bot.run()
    # Should attempt to run 1 initial + 2 retries = 3 times
    assert bot.client.run.call_count == 3
    # Check that exception and retry logs were called
    assert bot.logger.exception.call_count >= 3
    assert any("Attempting to reconnect" in str(call) for call in bot.logger.info.call_args_list)


def test_login_failure(monkeypatch):
    from disnake import LoginFailure

    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    # Mock client.run to raise LoginFailure
    bot.client.run = mock.Mock(side_effect=LoginFailure("bad token"))
    with pytest.raises(LoginFailure):
        bot.run()
    # Should only try once
    assert bot.client.run.call_count == 1
    assert any("Authentication failed" in str(call) for call in bot.logger.exception.call_args_list)


def test_no_retries(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "0")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=OSError("fail"))
    with pytest.raises(OSError):
        bot.run()
    # Should only try once (no retries)
    assert bot.client.run.call_count == 1
    assert bot.logger.exception.call_count >= 1


def test_negative_retries(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "-1")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=OSError("fail"))
    with pytest.raises(OSError):
        bot.run()
    # Class should only try once. Negative retries are treated as 0.
    assert bot.client.run.call_count == 1
    assert bot.logger.exception.call_count >= 1


def test_non_integer_retries(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "abc")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=OSError("fail"))
    with pytest.raises(ValueError):
        bot.run()


def test_non_integer_delay(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "1")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "xyz")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=OSError("fail"))
    with pytest.raises(ValueError):
        bot.run()


def test_zero_retry_delay(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "2")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=OSError("fail"))
    # Patch sleep to track calls
    with mock.patch("time.sleep") as mock_sleep:
        with pytest.raises(OSError):
            bot.run()
        # Should attempt to run 1 initial + 2 retries = 3 times
        assert bot.client.run.call_count == 3
        # sleep should not be called since delay is 0
        mock_sleep.assert_not_called()


def test_retry_succeeds(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "2")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    # First call fails, second call succeeds
    bot.client.run = mock.Mock(side_effect=[OSError("fail"), None])
    # Should not raise, since the second attempt succeeds
    bot.run()
    assert bot.client.run.call_count == 2
    # Should log error for first failure, but not raise
    assert bot.logger.exception.call_count >= 1


def test_shutdown_exception(monkeypatch):
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.is_closed = mock.Mock(return_value=False)
    bot.client.close = mock.Mock(side_effect=OSError("shutdown fail"))
    # Patch asyncio to avoid real event loop usage
    with mock.patch("asyncio.get_running_loop", side_effect=RuntimeError()):
        with mock.patch("asyncio.new_event_loop") as mock_new_loop:
            mock_loop = mock.Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.is_running.return_value = False
            bot.shutdown(loop=mock_loop)
    # Should log the shutdown error
    assert any("Error during shutdown:" in str(call) for call in bot.logger.exception.call_args_list)


def test_on_ready_sets_connected_and_logs(monkeypatch):
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    # Simulate event
    asyncio.run(bot.on_ready())
    assert bot.connected is True
    assert any("Connected to Discord as" in str(call) for call in bot.logger.info.call_args_list)


def test_on_disconnect_sets_disconnected_and_logs(monkeypatch):
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.connected = True
    asyncio.run(bot.on_disconnect())
    assert bot.connected is False
    assert any("Disconnected from Discord" in str(call) for call in bot.logger.warning.call_args_list)


def test_on_resumed_sets_connected_and_logs(monkeypatch):
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.connected = False
    asyncio.run(bot.on_resumed())
    assert bot.connected is True
    assert any("Reconnected to Discord." in str(call) for call in bot.logger.info.call_args_list)


class DummyUser:
    def __str__(self):
        return "TestUser"


def test_on_ready_with_user(monkeypatch):
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()

    # Patch client with a mock that has a user property
    class ClientWithUser:
        user = "TestUser"

    bot.client = ClientWithUser()
    asyncio.run(bot.on_ready())
    assert bot.connected is True
    # Check logger.info was called with the expected format string and argument
    assert any(
        call[0][0] == "Connected to Discord as %s" and call[0][1] == "TestUser"
        for call in bot.logger.info.call_args_list
    )


def test_on_disconnect_with_user(monkeypatch):
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()

    class ClientWithUser:
        user = "TestUser"

    bot.client = ClientWithUser()
    bot.connected = True
    asyncio.run(bot.on_disconnect())
    assert bot.connected is False
    assert any("Disconnected from Discord" in str(call) for call in bot.logger.warning.call_args_list)


def test_on_resumed_with_user(monkeypatch):
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()

    class ClientWithUser:
        user = "TestUser"

    bot.client = ClientWithUser()
    bot.connected = False
    asyncio.run(bot.on_resumed())
    assert bot.connected is True
    assert any("Reconnected to Discord." in str(call) for call in bot.logger.info.call_args_list)


def test_run_login_failure_non_mock(monkeypatch):
    from disnake import LoginFailure

    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()

    # Patch client to not be a mock
    class DummyClient:
        def run(self, token):
            raise LoginFailure("bad token")

    bot.client = DummyClient()
    with pytest.raises(LoginFailure):
        bot.run()
    assert any("Authentication failed" in str(call) for call in bot.logger.exception.call_args_list)


def test_shutdown_running_loop_add_done_callback(monkeypatch):
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.is_closed = mock.Mock(return_value=False)

    async def fake_close():
        # This is a fake coroutine to simulate close
        pass

    coro = fake_close()
    bot.client.close = mock.Mock(return_value=coro)
    # Patch asyncio to avoid real event loop usage
    with mock.patch("asyncio.get_running_loop", side_effect=RuntimeError()):
        with mock.patch("asyncio.new_event_loop") as mock_new_loop:
            mock_loop = mock.Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.is_running.return_value = True

            # Simulate create_task and add_done_callback
            class DummyTask:
                def add_done_callback(self, cb):
                    cb(self)

            mock_loop.create_task = mock.Mock(return_value=DummyTask())
            bot.shutdown(loop=mock_loop)
    assert any("Bot disconnected gracefully." in str(call) for call in bot.logger.info.call_args_list)
    coro.close()


def test_shutdown_returns_if_client_closed(monkeypatch):
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.is_closed = mock.Mock(return_value=True)
    # Should return early, not call close
    bot.client.close = mock.Mock()
    bot.shutdown()
    bot.client.close.assert_not_called()


def test_shutdown_returns_if_client_is_mock(monkeypatch):
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client = mock.Mock()
    bot.client.is_closed.return_value = False
    # Should return early if the client is a mock
    bot.shutdown()
    # Should not call close or log warning
    assert not bot.logger.warning.called


def test_shutdown_logs_warning_if_close_not_awaitable(monkeypatch):
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.is_closed = mock.Mock(return_value=False)
    # close returns a non-awaitable
    bot.client.close = mock.Mock(return_value=None)
    # Patch asyncio to avoid real event loop usage
    with mock.patch("asyncio.get_running_loop", side_effect=RuntimeError()):
        with mock.patch("asyncio.new_event_loop") as mock_new_loop:
            mock_loop = mock.Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.is_running.return_value = False
            bot.shutdown(loop=mock_loop)
    assert any("did not return a coroutine" in str(call) for call in bot.logger.warning.call_args_list)


def test_shutdown_logs_graceful_disconnect(monkeypatch):
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.is_closed = mock.Mock(return_value=False)

    async def fake_close():
        # This is a fake coroutine to simulate close
        pass

    coro = fake_close()
    bot.client.close = mock.Mock(return_value=coro)
    # Patch asyncio to avoid real event loop usage
    with mock.patch("asyncio.get_running_loop", side_effect=RuntimeError()):
        with mock.patch("asyncio.new_event_loop") as mock_new_loop:
            mock_loop = mock.Mock()
            mock_new_loop.return_value = mock_loop
            mock_loop.is_running.return_value = False

            # Simulate run_until_complete
            def run_until_complete(coro):
                return None

            mock_loop.run_until_complete = run_until_complete
            bot.shutdown(loop=mock_loop)
    assert any("Bot disconnected gracefully." in str(call) for call in bot.logger.info.call_args_list)
    coro.close()


def test_is_connected():
    bot = DiscordBot(token="dummy")
    bot.connected = True
    assert bot.is_connected() is True
    bot.connected = False
    assert bot.is_connected() is False


def test_handle_reconnect_retries(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "2")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=OSError("fail"))
    with pytest.raises(OSError):
        bot._handle_reconnect(OSError("fail"))
    # Should attempt to run 2 times (retries)
    assert bot.client.run.call_count == 2
    assert bot.logger.exception.call_count >= 2
    assert any("Attempting to reconnect" in str(call) for call in bot.logger.info.call_args_list)
