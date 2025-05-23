"""
Database manager for handling database operations.
"""
import os
from typing import Optional

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base


class DatabaseManager:
    """
    Manages database operations for the Foxhole Automated Quartermaster (FAQ).
    """

    def __init__(self):
        """
        Initialize the database manager.
        """
        # Get database URL from environment variables
        self.database_url = os.getenv(
            "DATABASE_URL",
            "sqlite+aiosqlite:///foxhole_logistics.db"
        )
        
        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            echo=os.getenv("DEBUG", "False").lower() == "true",
        )
        
        # Create async session factory
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        logger.info(f"Database manager initialized with URL: {self.database_url}")
    
    async def initialize(self):
        """
        Initialize the database by creating all tables.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
    
    async def get_session(self) -> AsyncSession:
        """
        Get a new database session.
        
        Returns:
            AsyncSession: A new database session.
        """
        return self.async_session()
    
    async def close(self):
        """
        Close the database connection.
        """
        await self.engine.dispose()
        logger.info("Database connection closed") 