"""Client functions for interacting with FoxAPI and updating the local database with war, map, and report data."""

import datetime
from dependencies.FoxAPI.FoxAPI.foxapi.foxapi import FoxAPI
from data.db.db import Map, MapDynamic, MapStatic, War, WarReport, initialize_db

# Initialize FoxAPI instance (singleton recommended)
foxapi = FoxAPI()

# Data access functions using FoxAPI
def get_war():
    """
    Fetches current war data from FoxAPI and updates the database.
    Returns the war data as a dict.
    """
    data = foxapi.get_war_sync()
    # Optionally update DB for historical tracking
    War.replace(
        war_id=data['warId'],
        start_time=datetime.datetime.fromtimestamp(data['warStartTime'] / 1000, tz=datetime.timezone.utc),
        resistance_phase=int(data['resistance']),
        last_updated=datetime.datetime.now(datetime.timezone.utc)
    ).execute()
    return data


def get_maps():
    """
    Fetches map list from FoxAPI and updates the database.
    Returns the list of maps as a list of dicts.
    """
    data = foxapi.get_maps_sync()
    for m in data:
        Map.replace(name=m['code'], display_name=m['name'], last_updated=datetime.datetime.now(datetime.timezone.utc)).execute()
    return data

def get_war_report(map_name):
    """
    Fetches war report for a map from FoxAPI and updates the database.
    Returns the report as a dict.
    """
    data = foxapi.get_war_report_sync(map_name)
    WarReport.replace(
        map_name=map_name,
        casualties=data.get('totalCasualties', 0),
        enlistments=data.get('totalEnlistments', 0),
        last_updated=datetime.datetime.now(datetime.timezone.utc)
    ).execute()
    return data

def get_map_static(map_name):
    """
    Fetches static map data from FoxAPI and updates the database.
    Returns the static data as a dict.
    """
    data = foxapi.get_static_sync(map_name)
    MapStatic.replace(
        map_name=map_name,
        data=str(data),  # Store as stringified JSON
        last_updated=datetime.datetime.now(datetime.timezone.utc)
    ).execute()
    return data

def get_map_dynamic(map_name):
    """
    Fetches dynamic map data from FoxAPI and updates the database.
    Returns the dynamic data as a dict.
    """
    data = foxapi.get_dynamic_sync(map_name)
    MapDynamic.replace(
        map_name=map_name,
        data=str(data),  # Store as stringified JSON
        last_updated=datetime.datetime.now(datetime.timezone.utc)
    ).execute()
    return data

# Call this at startup
def setup():
    initialize_db()

# --- Aggregated Hexagon Data ---
def get_hexagon_data(map_name):
    """
    Returns a HexagonObject for the given map, containing war report, static, dynamic, captured towns, and casualty rate.
    Uses FoxAPI's get_hexagon_data_sync for all-in-one access.
    """
    return foxapi.get_hexagon_data_sync(map_name)

# Example usage:
# hex_data = get_hexagon_data('Deadlands')
# print(hex_data.war_report)
# print(hex_data.static)
# print(hex_data.dynamic)
# print(hex_data.captured_towns)
# print(hex_data.casualty_rate)