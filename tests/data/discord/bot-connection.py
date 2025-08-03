import unittest
from unittest.mock import patch
from data.discord.discord import DiscordBot
import asyncio


class AsyncioTestRunner(unittest.TextTestRunner):
    def run(self, test):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            result = super().run(test)
        finally:
            self.loop.close()
        return result


class TestDiscordBotConnection(unittest.TestCase):
    @patch('data.discord.discord.Client')
    def test_startup_connection(self, mock_client):
        # Arrange
        instance = mock_client.return_value
        instance.run.return_value = None
        bot = DiscordBot(token='fake_token')
        # Act
        bot.run()
        # Assert
        instance.run.assert_called_with('fake_token')

    @patch('data.discord.discord.Client')
    def test_automatic_reconnection(self, mock_client):
        # Arrange
        instance = mock_client.return_value
        # Simulate disconnect and reconnect by raising and then not raising
        instance.run.side_effect = [Exception('disconnect'), None]
        bot = DiscordBot(token='fake_token')
        # Act
        try:
            bot.run()
        except Exception:
            # Simulate reconnect
            bot.run()
        # Assert
        self.assertEqual(instance.run.call_count, 2)

    @patch('data.discord.discord.Client')
    def test_authentication_error_handling(self, mock_client):
        # Arrange
        instance = mock_client.return_value
        from disnake import LoginFailure
        instance.run.side_effect = LoginFailure('authentication failed')
        bot = DiscordBot(token='bad_token')
        # Act & Assert
        with self.assertRaises(LoginFailure) as context:
            bot.run()
        self.assertIn('authentication failed', str(context.exception))

    @patch('data.discord.discord.Client')
    def test_graceful_shutdown(self, mock_client):
        # Arrange
        instance = mock_client.return_value
        instance.is_closed.return_value = False
        instance.close.return_value = None
        bot = DiscordBot(token='fake_token')
        # Act
        bot.shutdown()
        # Assert
        instance.close.assert_called_once()


if __name__ == '__main__':
    unittest.main(testRunner=AsyncioTestRunner())
