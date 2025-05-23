"""
Pytest configuration and fixtures.
"""
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base, LocationType, TaskType, TaskStatus, ProductionLocationType, UrgencyLevel, TransportLoadType, ItemCategory

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"
TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    engine = create_engine(TEST_DATABASE_URL, echo=True)
    yield engine
    # Cleanup
    engine.dispose()
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture(scope="session")
def tables(engine):
    """Create all database tables."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(engine, tables) -> Generator[Session, None, None]:
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest_asyncio.fixture(scope="session")
async def async_engine(event_loop):
    """Create an async test database engine."""
    engine = create_async_engine(TEST_ASYNC_DATABASE_URL, echo=True)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new async database session for a test."""
    async_session = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
def sample_regiment_data():
    """Sample data for creating a regiment."""
    return {
        "regiment_id": "123456789",
        "name": "Test Regiment"
    }

@pytest.fixture
async def regiment(async_session, sample_regiment_data):
    """Create a sample regiment for testing."""
    regiment = Regiment(**sample_regiment_data)
    async_session.add(regiment)
    await async_session.commit()
    return regiment

@pytest.fixture
def sample_location_data():
    """Sample location data for tests."""
    return {
        "name": "Test Location",
        "type": LocationType.FACTORY,
        "regiment_id": "123456789"
    }

@pytest.fixture
async def location(async_session, sample_location_data):
    """Create a sample location for testing."""
    location = Location(**sample_location_data)
    async_session.add(location)
    await async_session.commit()
    return location

@pytest.fixture
def sample_item_data():
    """Sample item data for tests."""
    return {
        "name": "Test Item",
        "category": ItemCategory.AMMUNITION,
        "description": "Test description",
        "importance": 1,
        "can_be_produced": True,
        "production_facility": ProductionLocationType.FACTORY
    }

@pytest.fixture
async def item(async_session, sample_item_data):
    """Create a sample item for testing."""
    item = Item(**sample_item_data)
    async_session.add(item)
    await async_session.commit()
    return item

@pytest.fixture
def sample_recipe_data():
    """Sample recipe data for tests."""
    return {
        "name": "Test Recipe",
        "description": "Test recipe description",
        "production_facility": ProductionLocationType.FACTORY,
        "production_time": 60,
        "output_quantity": 1
    }

@pytest.fixture
async def recipe(async_session, sample_recipe_data):
    """Create a sample recipe for testing."""
    recipe = Recipe(**sample_recipe_data)
    async_session.add(recipe)
    await async_session.commit()
    return recipe

@pytest.fixture
def sample_inventory_data():
    """Sample inventory data for tests."""
    return {
        "quantity": 100,
        "location_id": 1,
        "item_id": 1
    }

@pytest.fixture
async def inventory(async_session, sample_inventory_data):
    """Create a sample inventory for testing."""
    inventory = Inventory(**sample_inventory_data)
    async_session.add(inventory)
    await async_session.commit()
    return inventory

@pytest.fixture
def sample_task_data():
    """Sample task data for tests."""
    return {
        "type": TaskType.PRODUCTION,
        "status": TaskStatus.PENDING,
        "urgency": UrgencyLevel.NORMAL,
        "location_id": 1,
        "item_id": 1,
        "quantity": 100
    }

@pytest.fixture
async def task(async_session, sample_task_data):
    """Create a sample task for testing."""
    task = Task(**sample_task_data)
    async_session.add(task)
    await async_session.commit()
    return task

@pytest.fixture
def sample_location_buffer_data():
    """Sample location buffer data for tests."""
    return {
        "location_id": 1,
        "item_id": 1,
        "min_quantity": 50,
        "max_quantity": 200
    }

@pytest.fixture
async def location_buffer(async_session, sample_location_buffer_data):
    """Create a sample location buffer for testing."""
    buffer = LocationBuffer(**sample_location_buffer_data)
    async_session.add(buffer)
    await async_session.commit()
    return buffer 