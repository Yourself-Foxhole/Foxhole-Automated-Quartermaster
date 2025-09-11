"""DiscordGuild: Persistent data model for a Discord server (guild).

Stores user permissions, channel IDs, configurations, and other server-specific data.
"""  # noqa: E501, RUF100

from persistent import Persistent  # type: ignore[import]
from persistent.mapping import PersistentMapping  # type: ignore[import]


class DiscordGuild(Persistent):
    """Persistent Discord server (guild) data container.

    Stores configuration, channel IDs, and user permissions for a Discord
    guild.
    """

    def __init__(self, guild_id: int) -> None:
        """Initialize a DiscordGuild with a guild ID.

        Args:
            guild_id (int): The Discord guild (server) ID.

        """
        self.guild_id = guild_id
        # Arbitrary config values
        self.config: PersistentMapping = PersistentMapping()
        # e.g., {'log': 123456789, ...}
        self.channel_ids: PersistentMapping = PersistentMapping()
        # e.g., {user_id: ['admin', ...]}
        self.user_permissions: PersistentMapping = PersistentMapping()

    def set_config(self, key: str, value: object) -> None:
        """Set a configuration value for the guild.

        Args:
            key (str): The config key.
            value (object): The value to store.

        """
        self.config[key] = value
        self._p_changed = True

    def get_config(self, key: str, default: object = None) -> object:
        """Get a configuration value for the guild.

        Args:
            key (str): The config key.
            default (object, optional): Default value if key is not found.

        Returns:
            object: The config value or default.

        """
        return self.config.get(key, default)

    def set_channel_id(self, name: str, channel_id: int) -> None:
        """Set a channel ID for a named channel type.

        Args:
            name (str): The channel type/name (e.g., 'log').
            channel_id (int): The Discord channel ID.

        """
        self.channel_ids[name] = channel_id
        self._p_changed = True

    def get_channel_id(self, name: str) -> int | None:
        """Get a channel ID by name.

        Args:
            name (str): The channel type/name.

        Returns:
            int | None: The channel ID or None if not set.

        """
        return self.channel_ids.get(name)

    def set_user_permissions(
        self,
        user_id: int,
        permissions: list[str],
    ) -> None:
        """Set permissions for a user in the guild.

        Args:
            user_id (int): The Discord user ID.
            permissions (list[str]): List of permission strings.

        """
        self.user_permissions[user_id] = permissions
        self._p_changed = True

    def get_user_permissions(self, user_id: int) -> list[str]:
        """Get permissions for a user in the guild.

        Args:
            user_id (int): The Discord user ID.

        Returns:
            list[str]: List of permission strings (empty if none).

        """
        return self.user_permissions.get(user_id, [])
