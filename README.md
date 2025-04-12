# Foxhole Logistics Bot

A Discord bot for coordinating logistics operations in the game Foxhole. The bot uses a pull-based model where demands at the frontline generate upstream tasks.

## Project Overview

The Foxhole Logistics Bot is designed to help players coordinate logistics operations in the game Foxhole. It tracks inventory levels, generates tasks based on deficits, and helps players coordinate the production and transportation of resources.

### Key Features

- **Pull-Based Model**: Demands at the frontline generate upstream tasks
- **Inventory Tracking**: Track inventory levels at various locations
- **Task Management**: Create, assign, and track logistics tasks
- **Production Support**: Support for different production methods (Factory, MPF, Facility)
- **Real-Time Notifications**: Alert players about critical shortages

## Technology Stack

- **Programming Language**: Python 3.9+
- **Discord Library**: Discord.py
- **Database**: SQLite
- **ORM**: SQLAlchemy
- **Task Scheduling**: APScheduler
- **Testing**: pytest

## Project Structure

```
src/
├── bot/                  # Discord bot implementation
├── database/             # Database models and manager
│   ├── database_manager.py  # Database connection and session management
│   └── models.py             # SQLAlchemy models
├── services/             # Business logic services
│   ├── task_manager.py       # Task creation and management
│   ├── stock_manager.py      # Inventory tracking
│   ├── location_manager.py   # Location management
│   ├── recipe_manager.py     # Recipe and production management
│   └── notification_engine.py # Notification system
└── utils/                # Utility functions
    ├── config.py             # Configuration management
    └── logging.py            # Logging setup
```

## Database Models

The bot uses the following core models:

- **Regiment**: Represents a Discord server
- **Location**: Represents a location in the game (hub, base, facility)
- **Item**: Represents an item in the game
- **Recipe**: Defines how items are produced
- **Inventory**: Tracks item quantities at locations
- **Task**: Represents a logistics task
- **LocationBuffer**: Defines target buffer levels for items at locations

## Getting Started

### Prerequisites

- Python 3.9+
- Discord Bot Token
- SQLite

### Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your Discord bot token
4. Run the bot: `python src/bot/main.py`

## Test Plan

1. **Database Initialization Tests**
   - Verify all tables are created correctly
   - Test foreign key constraints and relationships

2. **Model Validation Tests**
   - Test enum validation for all enumerated fields
   - Verify cascade behavior for related entities

3. **CRUD Operation Tests**
   - Test creation, reading, updating, and deletion of all entities
   - Verify relationship integrity during operations

4. **Business Logic Tests**
   - Test task generation based on inventory deficits
   - Verify priority calculation for tasks
   - Test the pull-based model logic

5. **Integration Tests**
   - Test interaction between models for complex operations
   - Verify transaction integrity for multi-step operations

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Foxhole game developers
- Discord.py community
- SQLAlchemy community
