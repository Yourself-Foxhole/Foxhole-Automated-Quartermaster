"""StaticWarData: Handles caching and retrieval of static war data in the database.

- Caches /worldconquest/war (war start, etc.)
- Caches /worldconquest/maps (static map list)
- Caches /worldconquest/maps/:map/static (static map data and buildings)
"""
import datetime
from data.warapi import war_api_client

class StaticWarData:
    """Caches and retrieves static war data from the database using war_api_client."""

    @staticmethod
    def cache_war():
        """Fetch and cache /worldconquest/war response using war_api_client."""
        war_data = war_api_client.get_war()
        return war_data

    @staticmethod
    def cache_maps():
        """Fetch and cache /worldconquest/maps response using war_api_client."""
        maps_data = war_api_client.get_maps()
        return maps_data

    @staticmethod
    def cache_map_static(map_name: str):
        """Fetch and cache /worldconquest/maps/:map/static response using war_api_client, and cache buildings."""
        static_data = war_api_client.get_map_static(map_name)
        # Cache buildings in Building table
        from data.db.db import Building
        for b in static_data.get('mapTextItems', []):
            Building.replace(
                id=f"{map_name}:{b['id']}",
                map_name=map_name,
                type=b.get('iconType', 'Unknown'),
                region=b.get('regionId'),
                x=b.get('x'),
                y=b.get('y'),
                data=str(b),
                last_updated=datetime.datetime.now(datetime.timezone.utc)
            ).execute()
        return static_data

    @staticmethod
    def get_cached_war():
        """Retrieve the cached war data."""
        from data.db.db import War
        return War.select().order_by(War.last_updated.desc()).first()

    @staticmethod
    def get_cached_maps():
        """Retrieve the cached maps list."""
        from data.db.db import Map
        return list(Map.select())

    @staticmethod
    def get_cached_map_static(map_name: str):
        """Retrieve the cached static map data for a map."""
        from data.db.db import MapStatic
        return MapStatic.get_or_none(MapStatic.map_name == map_name)

    @staticmethod
    def get_cached_buildings(map_name: str = None):
        """Retrieve cached buildings, optionally filtered by map_name."""
        from data.db.db import Building
        query = Building.select()
        if map_name:
            query = query.where(Building.map_name == map_name)
        return list(query)
