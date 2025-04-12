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

from src.database.models import Base

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"
TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

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

@pytest_asyncio.fixture
async def async_engine():
    """Create an async test database engine."""
    engine = create_async_engine(TEST_ASYNC_DATABASE_URL, echo=True)
    yield engine
    await engine.dispose()
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new async database session for a test."""
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest.fixture
def sample_regiment_data():
    """Sample regiment data for tests."""
    return {
        "regiment_id": "123456789",
        "name": "Test Regiment"
    }

@pytest.fixture
def sample_location_data():
    """Sample location data for tests."""
    return {
        "name": "Test Location",
        "location_type": "FRONTLINE_HUB",
        "coordinates": "F5-2"
    }

@pytest.fixture
def sample_item_data():
    """Sample item data for tests."""
    return {
        "name": "7.62mm",
        "category": "AMMUNITION",
        "is_crate_packable": True,
        "crate_size": 20
    }

@pytest.fixture
def sample_recipe_data():
    """Sample recipe data for tests."""
    return {
        "output_quantity": 20,
        "production_location_type": "FACTORY",
        "production_time": 60,
        "mpf_discount_eligible": True
    }

@pytest.fixture
def sample_inventory_data():
    """Sample inventory data for tests."""
    return {
        "quantity": 100,
    }

@pytest.fixture
def sample_task_data():
    """Sample task data for tests."""
    return {
        "task_type": "MANUFACTURE_PENDING",
        "quantity": 100,
        "status": "UNCLAIMED",
        "priority_score": 5,
        "urgency": "MEDIUM"
    }

@pytest.fixture
def sample_location_buffer_data():
    """Sample location buffer data for tests."""
    return {
        "target_quantity": 1000,
        "critical_threshold_percent": 25,
        "default_production_location": "FACTORY",
        "default_transport_load_type": "FTL",
        "priority_score": 3
    } 