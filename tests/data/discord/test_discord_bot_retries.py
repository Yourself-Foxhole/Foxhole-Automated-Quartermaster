import pytest
from hypothesis import given, strategies as st
from hypothesis import settings, HealthCheck
from unittest import mock

from data.discord.discord import DiscordBot

def test_get_max_retries_default(monkeypatch):
    monkeypatch.delenv("DISCORD_BOT_MAX_RETRIES", raising=False)
    bot = DiscordBot(token="dummy")
    assert bot._get_max_retries() == 3

def test_get_max_retries_invalid(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "not-an-int")
    bot = DiscordBot(token="dummy")
    with pytest.raises(ValueError):
        bot._get_max_retries()

def test_get_max_retries_negative(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "-5")
    bot = DiscordBot(token="dummy")
    assert bot._get_max_retries() == 0

@given(val=st.integers(min_value=-100, max_value=1000))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_get_max_retries_hypothesis(monkeypatch, val):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", str(val))
    bot = DiscordBot(token="dummy")
    expected = max(0, val)
    assert bot._get_max_retries() == expected

def test_get_retry_delay_default(monkeypatch):
    monkeypatch.delenv("DISCORD_BOT_RETRY_DELAY", raising=False)
    bot = DiscordBot(token="dummy")
    assert bot._get_retry_delay() == 15

def test_get_retry_delay_invalid(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "not-an-int")
    bot = DiscordBot(token="dummy")
    with pytest.raises(ValueError):
        bot._get_retry_delay()

@given(val=st.integers(min_value=-100, max_value=1000))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_get_retry_delay_hypothesis(monkeypatch, val):
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", str(val))
    bot = DiscordBot(token="dummy")
    assert bot._get_retry_delay() == val

@given(
    retries=st.integers(min_value=0, max_value=5),
    delay=st.integers(min_value=0, max_value=2)
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_handle_reconnect_retries(monkeypatch, retries, delay):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", str(retries))
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", str(delay))
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=Exception("fail"))
    # Patch sleep to avoid real delay
    with mock.patch("time.sleep") as mock_sleep:
        if retries == 0:
            with pytest.raises(Exception):
                bot._handle_reconnect(Exception("fail"))
            assert bot.client.run.call_count == 0
        else:
            with pytest.raises(Exception):
                bot._handle_reconnect(Exception("fail"))
            assert bot.client.run.call_count == retries
            if delay > 0 and retries > 1:
                mock_sleep.assert_called_with(delay)
            else:
                mock_sleep.assert_not_called()
    # Check logging
    assert bot.logger.exception.call_count >= max(0, retries)
    if retries > 0:
        assert any("Attempting to reconnect" in str(call) for call in bot.logger.info.call_args_list)


def test_handle_reconnect_success(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "3")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    # First call fails, second call succeeds
    bot.client.run = mock.Mock(side_effect=[Exception("fail"), None])
    with mock.patch("time.sleep") as mock_sleep:
        bot._handle_reconnect(Exception("fail"))
    assert bot.client.run.call_count == 2
    assert bot.logger.error.call_count >= 1
    assert any("Attempting to reconnect" in str(call) for call in bot.logger.info.call_args_list)
    mock_sleep.assert_not_called()


def test_handle_reconnect_raises_last(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "2")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=[Exception("fail1"), Exception("fail2")])
    with mock.patch("time.sleep"):
        with pytest.raises(Exception) as exc:
            bot._handle_reconnect(Exception("fail0"))
    assert "fail2" in str(exc.value)


def test_handle_reconnect_with_delay(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "3")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "2")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=Exception("fail"))
    with mock.patch("time.sleep") as mock_sleep:
        with pytest.raises(Exception):
            bot._handle_reconnect(Exception("fail"))
        # Should sleep between each retry except the last
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(2)


def test_handle_reconnect_one_retry(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "1")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "1")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=Exception("fail"))
    with mock.patch("time.sleep") as mock_sleep:
        with pytest.raises(Exception):
            bot._handle_reconnect(Exception("fail"))
        assert bot.client.run.call_count == 1
        mock_sleep.assert_not_called()


def test_handle_reconnect_keyboard_interrupt(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "2")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        bot._handle_reconnect(Exception("fail"))
    assert bot.client.run.call_count == 1


def test_handle_reconnect_logs_all(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "2")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=Exception("fail"))
    with pytest.raises(Exception):
        bot._handle_reconnect(Exception("fail"))
    # Should log error and exception for each attempt
    assert bot.logger.error.call_count == 2
    assert bot.logger.exception.call_count == 2


def test_handle_reconnect_success_on_last(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "3")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")
    bot = DiscordBot(token="dummy")
    bot.logger = mock.Mock()
    bot.client.run = mock.Mock(side_effect=[Exception("fail1"), Exception("fail2"), None])
    with mock.patch("time.sleep"):
        bot._handle_reconnect(Exception("fail0"))
    assert bot.client.run.call_count == 3
    assert bot.logger.exception.call_count == 2
    assert any("Attempting to reconnect" in str(call) for call in bot.logger.info.call_args_list)


def test_handle_reconnect_logger_raises(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_MAX_RETRIES", "2")
    monkeypatch.setenv("DISCORD_BOT_RETRY_DELAY", "0")
    bot = DiscordBot(token="dummy")
    # logger.error raises, should not break retry loop
    class RaisingLogger:
        # We don't need full methods inside a unit test, just stubs
        def info(self, *a, **k): pass # NOSONAR
        def error(self, *a, **k): raise Exception("log error") # NOSONAR
        def exception(self, *a, **k): pass # NOSONAR
    bot.logger = RaisingLogger()
    bot.client.run = mock.Mock(side_effect=Exception("fail"))
    with pytest.raises(Exception):
        bot._handle_reconnect(Exception("fail"))
    assert bot.client.run.call_count == 2
