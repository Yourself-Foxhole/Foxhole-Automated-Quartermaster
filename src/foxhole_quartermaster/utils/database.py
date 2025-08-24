"""
Database management utilities for the multi-tenant Discord bot.
"""

import logging
import os
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from ..models import Base


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'sqlite:///foxhole_quartermaster.db')
        self.engine = None
        self.SessionLocal = None
        
    async def initialize(self) -> None:
        """Initialize database engine and create tables."""
        logger.info(f"Initializing database: {self.database_url}")
        
        # Configure engine based on database type
        if self.database_url.startswith('sqlite'):
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )
        else:
            self.engine = create_engine(
                self.database_url,
                echo=False
            )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Create all tables
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created/verified")
        
        # Initialize default data if needed
        await self._initialize_default_data()
    
    async def _initialize_default_data(self) -> None:
        """Initialize any default data needed by the application."""
        with self.get_session() as session:
            # Check if we need to create any default server admin users
            # This would be configurable via environment variables
            default_admin_discord_id = os.getenv('DEFAULT_ADMIN_DISCORD_ID')
            if default_admin_discord_id:
                from ..models import User
                admin = session.query(User).filter(
                    User.discord_id == default_admin_discord_id
                ).first()
                
                if not admin:
                    admin = User(
                        discord_id=default_admin_discord_id,
                        username="DefaultAdmin",
                        is_server_admin=True
                    )
                    session.add(admin)
                    session.commit()
                    logger.info(f"Created default server admin user: {default_admin_discord_id}")
    
    def get_session(self) -> Session:
        """Get a database session."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            with self.session_scope() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global db_manager
    if not db_manager:
        db_manager = DatabaseManager()
    return db_manager