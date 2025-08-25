# Foxhole Automated Quartermaster

Discord Bot to track Logistics in the game of Foxhole, tracking what to move where, and when.

## Multi-Tenant Architecture

This bot is designed with a comprehensive multi-tenant architecture that allows multiple regiments (Discord servers) to use the same bot instance while maintaining complete data isolation and security.

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Discord Bot Token
- PostgreSQL or SQLite database (SQLite is used by default)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Yourself-Foxhole/Foxhole-Automated-Quartermaster.git
cd Foxhole-Automated-Quartermaster
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up configuration:
```bash
cp .env.example .env
# Edit .env with your Discord bot token and other settings
```

4. Run the bot:
```bash
python -m foxhole_quartermaster
```

### Bot Setup

1. **Add Bot to Discord Server**: Invite the bot to your Discord server with appropriate permissions.

2. **Register Your Regiment**: Use the `!setup_regiment` command in your server:
```
!setup_regiment "My Regiment Name" my-regiment-slug Colonial
```

3. **Add Members**: Add users to your regiment with appropriate roles:
```
!add_member @username end_user
!add_member @logistics_lead logistics_manager
```

## Key Features

### Multi-Tenant Support
- **Complete Data Isolation**: Each regiment's data is completely separate
- **Multiple Server Support**: One bot instance can serve dozens of Discord servers
- **Role-Based Access Control**: Granular permissions per tenant
- **Secure Operations**: No data leakage between regiments

### Role System
- **Server Admin**: Full control over all tenants (for bot operators)
- **Regiment Admin**: Full control over their regiment
- **Logistics Manager**: Can edit supply chains and production
- **End User**: Basic operations like accepting tasks

### Logistics Tracking
- **Supply Nodes**: Track inventory across multiple locations
- **Production Facilities**: Manage manufacturing and production queues
- **Task Management**: Assign and track logistics tasks
- **Real-time Updates**: Keep everyone informed of logistics status

## Commands

### Tenant Management
- `!setup_regiment <name> <slug> [faction]` - Register Discord server as regiment
- `!regiment_info` - Show regiment information
- `!add_member @user <role>` - Add user with role
- `!remove_member @user` - Remove user from regiment
- `!list_members` - List all regiment members

### Logistics Commands
- `!create_supply_node <name> <location> [type]` - Create supply tracking node
- `!list_supply_nodes` - List all supply nodes
- `!create_production_node <name> <location> [type]` - Create production facility
- `!list_production_nodes` - List all production facilities
- `!create_task <type> <title> [description]` - Create logistics task
- `!list_tasks [status]` - List tasks with optional filtering
- `!accept_task <task_id>` - Accept task assignment

### Admin Commands (Server Admin only)
- `!list_tenants` - List all registered tenants
- `!promote_server_admin @user` - Grant server admin privileges

## Architecture Overview

The bot implements a sophisticated multi-tenant architecture:

- **Tenant Abstraction**: Each regiment is a separate tenant with isolated data
- **Permission System**: Role-based access control with granular permissions
- **Database Design**: All data is scoped by tenant ID for complete isolation
- **Command Routing**: Automatic tenant detection and permission enforcement

For detailed architecture information, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Development

### Running Tests
```bash
pip install -r requirements-dev.txt
pytest tests/
```

### Code Quality
```bash
black src/ tests/
flake8 src/ tests/
mypy src/
```

## Security Considerations

- **Data Isolation**: No regiment can access another's data
- **Permission Enforcement**: All operations require appropriate roles
- **Audit Logging**: All operations are logged with full context
- **Token Security**: Bot tokens must be kept secure and not committed

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please ensure all tests pass and follow the existing code style.

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/Yourself-Foxhole/Foxhole-Automated-Quartermaster/issues).
