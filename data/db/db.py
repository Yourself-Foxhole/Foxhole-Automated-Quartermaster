"""Database models and setup for Foxhole Automated Quartermaster.

This module defines the Peewee ORM models and database setup for storing
persistent data related to the War API, onboarding, alerting, and logistics network.

Models include War, Map, WarReport, MapStatic, MapDynamic, Facility, Building, Region, Player,
  Task, and ProductionCalculationCache.

Call setup() once at application startup to ensure all tables exist.
"""

import datetime
from peewee import Model, CharField, IntegerField, DateTimeField, SqliteDatabase
from peewee import TextField, FloatField

# Database setup (adjust path as needed)
db = SqliteDatabase('data/warapi/warapi_cache.db')

class BaseModel(Model):
    """Base Peewee model using the shared database connection."""
    class Meta:
        database = db

class War(BaseModel):
    """Stores metadata about the current or past wars."""
    war_id = IntegerField(primary_key=True)
    start_time = DateTimeField()
    resistance_phase = IntegerField()
    last_updated = DateTimeField(default=datetime.datetime.utcnow)

class Map(BaseModel):
    """Stores map codes and display names for all regions in the war."""
    name = CharField(primary_key=True)
    display_name = CharField()
    last_updated = DateTimeField(default=datetime.datetime.utcnow)

class WarReport(BaseModel):
    """Stores war report statistics for a given map, such as casualties and enlistments."""
    map_name = CharField()
    casualties = IntegerField()
    enlistments = IntegerField()
    last_updated = DateTimeField(default=datetime.datetime.utcnow)

class MapStatic(BaseModel):
    """Stores static map data (e.g., structures, layout) as JSON for a given map."""
    map_name = CharField(primary_key=True)
    data = CharField()  # JSON as string
    last_updated = DateTimeField(default=datetime.datetime.utcnow)

class MapDynamic(BaseModel):
    """Stores dynamic map data (e.g., real-time state) as JSON for a given map."""
    map_name = CharField(primary_key=True)
    data = CharField()  # JSON as string
    last_updated = DateTimeField(default=datetime.datetime.utcnow)

class Facility(BaseModel):
    """Stores information about facilities (refineries, factories, etc.) in the network."""
    id = CharField(primary_key=True)
    map_name = CharField()
    type = CharField()  # e.g., Refinery, Factory, MPF, etc.
    region = CharField(null=True)
    x = FloatField(null=True)
    y = FloatField(null=True)
    data = TextField(null=True)  # JSON as string for extra info
    last_updated = DateTimeField(default=datetime.datetime.utcnow)

class Building(BaseModel):
    """Stores information about generic buildings and structures in the network."""
    id = CharField(primary_key=True)
    map_name = CharField()
    type = CharField()  # e.g., Storage Depot, Seaport, etc.
    region = CharField(null=True)
    x = FloatField(null=True)
    y = FloatField(null=True)
    data = TextField(null=True)
    last_updated = DateTimeField(default=datetime.datetime.utcnow)

class Region(BaseModel):
    """Stores metadata and extra data for map regions/hexes."""
    name = CharField(primary_key=True)
    display_name = CharField()
    data = TextField(null=True)
    last_updated = DateTimeField(default=datetime.datetime.utcnow)

class Player(BaseModel):
    """Stores player information and stats for leaderboards and tracking."""
    player_id = CharField(primary_key=True)
    name = CharField()
    stats = TextField(null=True)  # JSON as string
    last_updated = DateTimeField(default=datetime.datetime.utcnow)

class Task(BaseModel):
    """Stores tasks for onboarding, alerting, and logistics workflows."""
    id = CharField(primary_key=True)
    type = CharField()  # onboarding, alert, etc.
    status = CharField()  # open, closed, etc.
    data = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

class ProductionCalculationCache(BaseModel):
    """Stores cached production calculation results for a node and amount."""
    node_name = CharField()
    amount = FloatField()
    result_json = TextField()  # JSON string of calculation result
    last_updated = DateTimeField(default=datetime.datetime.utcnow)

    class Meta:
        indexes = ((('node_name', 'amount'), True),)  # Unique constraint

def setup():
    """
    Creates all database tables if they do not exist.
    Call this once at application startup to ensure schema is ready.
    """
    if db.is_closed():
        db.connect()
    db.create_tables([
        War, Map, WarReport, MapStatic, MapDynamic,
        Facility, Building, Region, Player, Task, ProductionCalculationCache
    ], safe=True)
    db.close()

def initialize_db():
    """
    Opens a connection to the database if it is not already open.
    Use this for short-lived DB access, not for schema setup.
    """
    if db.is_closed():
        db.connect()
