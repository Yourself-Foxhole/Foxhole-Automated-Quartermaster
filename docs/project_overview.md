# Foxhole Automated Quartermaster (FAQ) - Project Overview

## Project Structure

The project follows a modular architecture with clear separation of concerns:

```
Foxhole-Automated-Quartermaster/
├── src/
│   ├── database/
│   │   ├── models.py           # SQLAlchemy models
│   │   └── database_manager.py # Database connection management
│   ├── services/
│   │   ├── inventory.py        # Inventory management service
│   │   ├── task.py            # Task management service
│   │   └── recipe.py          # Recipe management service
│   └── bot/
│       └── discord_bot.py      # Discord bot implementation
├── tests/
│   ├── database/
│   │   ├── test_models.py      # Model tests
│   │   └── test_location_model.py # Location model tests
│   └── conftest.py            # Test configuration and fixtures
├── docs/
│   └── project_overview.md     # This documentation
├── requirements.txt           # Project dependencies
├── pytest.ini                # Pytest configuration
└── run_tests.py             # Test runner script
```

## Database Models

The project uses SQLAlchemy for database management with the following core models:

1. **Regiment**
   - Represents a Discord regiment/guild
   - Manages channels and roles
   - Tracks creation and update timestamps

2. **Location**
   - Represents in-game locations
   - Supports different location types (FRONTLINE_HUB, BACKLINE_HUB, etc.)
   - Manages relationships with items, tasks, and buffers

3. **Item**
   - Represents in-game items
   - Tracks item properties and categories
   - Manages relationships with recipes and inventory

4. **Recipe**
   - Defines manufacturing recipes
   - Tracks production requirements and outputs
   - Supports MPF discount eligibility

5. **Task**
   - Represents logistics tasks
   - Manages task status and priority
   - Tracks source and target locations

6. **LocationBuffer**
   - Manages inventory thresholds
   - Controls automatic task generation
   - Tracks priority scores

## Testing Infrastructure

The project implements a comprehensive testing framework using pytest:

### Test Configuration (`pytest.ini`)
- Configured test paths and patterns
- Defined test categories (unit, integration, database, etc.)
- Set up coverage reporting
- Configured environment variables for testing

### Test Fixtures (`conftest.py`)
- Database session management
- Sample data fixtures for all models
- Cleanup procedures
- Async test support

### Model Tests
1. **Regiment Tests** (`test_models.py`)
   - Creation and validation
   - Unique constraint testing
   - Relationship management
   - Cascade delete verification
   - Timestamp handling

2. **Location Tests** (`test_location_model.py`)
   - Location creation and validation
   - Type validation
   - Required field testing
   - Relationship testing (regiment, role, items)
   - Source/target relationship testing
   - Inventory and buffer relationships
   - Task relationship testing
   - Cascade delete verification

### Test Runner (`run_tests.py`)
- Custom test runner script
- Configurable test arguments
- Coverage reporting
- Project root path management

## Dependencies

Key project dependencies (from `requirements.txt`):

### Core Dependencies
- `discord.py==2.3.2` - Discord bot framework
- `SQLAlchemy==2.0.23` - Database ORM
- `aiosqlite==0.19.0` - Async SQLite support
- `alembic==1.12.1` - Database migrations

### Testing Dependencies
- `pytest==7.4.3` - Test framework
- `pytest-asyncio==0.21.1` - Async test support
- `pytest-cov==4.1.0` - Coverage reporting

### Utilities
- `python-dotenv==1.0.0` - Environment management
- `loguru==0.7.2` - Logging
- `APScheduler==3.10.4` - Task scheduling

### Type Checking
- `mypy==1.7.0` - Static type checking
- `sqlalchemy-stubs==0.4` - SQLAlchemy type stubs

## Next Steps

1. **Service Layer Implementation**
   - Implement inventory management service
   - Develop task management service
   - Create recipe management service

2. **Discord Bot Development**
   - Implement command handlers
   - Set up event listeners
   - Create user interaction flows

3. **Additional Testing**
   - Service layer tests
   - Integration tests
   - Bot command tests

4. **Documentation**
   - API documentation
   - User guide
   - Deployment guide 