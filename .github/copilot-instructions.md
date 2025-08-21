# Foxhole Automated Quartermaster
Discord Bot to track Logistics in the game of Foxhole, tracking what to move where, and when.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Repository Current State
**IMPORTANT**: This repository is currently in its initial state and contains only basic files:
- `.gitignore` (configured for Python projects)
- `LICENSE` (GPL v3)
- `README.md` (basic description)

There is no source code, dependencies, or build configuration present yet. The repository is set up for Python development based on the .gitignore configuration.

## Working Effectively

### Current Repository Validation
- Repository structure: `ls -la` shows only `.gitignore`, `LICENSE`, `README.md`
- Git status: `git --no-pager status` - should show clean working directory
- Python availability: `python3 --version` - Python 3.12.3 is available
- **DO NOT** attempt to build, test, or run code - no source code exists yet

### When Source Code is Added (Future)
The following instructions apply when the Discord bot code is implemented:

#### Python Environment Setup
- Install Python dependencies: `pip3 install -r requirements.txt` (when requirements.txt exists)
- Create virtual environment: `python3 -m venv venv && source venv/bin/activate`
- Install development dependencies: `pip3 install -r requirements-dev.txt` (when available)

#### Expected Build and Test Commands (When Applicable)
- **NEVER CANCEL**: Build/install may take 5-10 minutes. Set timeout to 15+ minutes.
- Run tests: `python3 -m pytest` or `python3 -m unittest discover` 
- **NEVER CANCEL**: Test suite may take 3-5 minutes. Set timeout to 10+ minutes.
- Code formatting: `python3 -m black .` (when black is configured)
- Linting: `python3 -m flake8` or `python3 -m pylint` (when configured)
- Type checking: `python3 -m mypy .` (when mypy is configured)

#### Running the Discord Bot (When Implemented)
- **CRITICAL**: Discord bots require a bot token to run
- Expected run command: `python3 main.py` or `python3 bot.py`
- Bot will fail without proper Discord token configuration
- Configuration likely in `.env` file or environment variables

## Validation Scenarios

### Current State Validation
- Verify repository structure: `ls -la` shows `.gitignore`, `LICENSE`, `README.md`, and `.github/` only
- Confirm Python is available: `python3 --version` returns Python 3.12.3
- Check pip availability: `pip3 --version` returns pip 24.0
- Check git status: `git --no-pager status` shows working directory status
- Test virtual environment creation: `python3 -m venv test_venv && rm -rf test_venv`
- Verify unittest availability: `python3 -c "import unittest; print('unittest available')"`

### Future Discord Bot Validation (When Code Exists)
- **MANUAL VALIDATION REQUIREMENT**: Always test Discord bot functionality manually
- Test bot startup: Bot should connect to Discord successfully
- Test basic commands: Verify bot responds to commands in Discord
- Test logistics tracking: Verify core Foxhole logistics functionality works
- Test data persistence: Verify data is saved and retrieved correctly
- **DO NOT** simply start and stop the application - execute real Discord interactions

### Discord Bot Workflow Testing (Validated Approach)
When implementing the Discord bot, use this validated testing approach:
```python
# Test bot without token (should fail safely)
python3 -c "
import asyncio
class TestBot:
    def __init__(self, token=None):
        self.token = token
    async def start(self):
        if not self.token:
            raise ValueError('Discord token required')
        print('Bot startup successful')

try:
    bot = TestBot()
    asyncio.run(bot.start())
except ValueError as e:
    print(f'✓ Correctly failed without token: {e}')
"
```
This pattern ensures proper error handling for missing Discord tokens.

### Development Workflow Validation
- Always run linting before committing changes
- Always run tests before submitting changes
- Verify Discord token configuration is secure (not committed to git)
- Test bot permissions in Discord server

## Expected Development Timeline

### Phase 1: Basic Setup (Not Yet Implemented)
- Add `requirements.txt` with Discord.py and other dependencies
- Create main bot file (`main.py` or `bot.py`)
- Add basic Discord bot configuration
- Implement simple ping/status commands

### Phase 2: Core Functionality (Future)
- Implement Foxhole logistics tracking
- Add database integration for persistent storage
- Create Discord slash commands for logistics operations
- Add user authentication and permissions

### Phase 3: Advanced Features (Future)
- Real-time logistics monitoring
- Integration with Foxhole game APIs (if available)
- Advanced reporting and analytics
- Multi-server support

## Common Tasks

### Repository Inspection
```bash
# Current repository structure
ls -la
# Output: .github/, .gitignore, LICENSE, README.md (plus git directory)

# Check Python availability  
python3 --version
# Output: Python 3.12.3

# Check pip availability
pip3 --version  
# Output: pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.12)

# View project description
cat README.md
# Output: Discord Bot to track Logistics in the game of Foxhole, tracking what to move where, and when.
```

### Git Operations
```bash
# Check repository status
git --no-pager status
# Shows current branch and working directory status

# View recent commits
git --no-pager log --oneline -5
# Output: Shows repository initialization and recent changes
```

## Important Notes

### Security Considerations
- **NEVER COMMIT DISCORD BOT TOKENS** to the repository
- Use environment variables or `.env` files (add to .gitignore)
- Verify bot permissions are minimal and appropriate
- Test with development Discord server before production

### Discord Bot Specific Warnings
- Discord bots require proper server permissions to function
- Bot tokens are sensitive and must be kept secure
- Rate limiting applies to Discord API calls
- Bot must be invited to Discord servers with correct permissions

### Build Time Expectations (Validated)
- **NEVER CANCEL**: Python package installation typically takes 2-10 minutes depending on dependencies
- **NEVER CANCEL**: Virtual environment creation takes 5-15 seconds (tested successfully)
- **NEVER CANCEL**: Test suite execution may take 3-5 minutes for comprehensive Discord bot tests
- **NEVER CANCEL**: Initial Discord bot connection may take 30-60 seconds (network dependent)
- **NEVER CANCEL**: Bot startup and authentication may take 1-2 minutes on first run
- Always use timeouts of 15+ minutes for installation commands
- Always use timeouts of 10+ minutes for test commands
- Always use timeouts of 5+ minutes for bot startup commands

## Troubleshooting

### Common Issues (When Code Exists)
- **Bot won't start**: Check Discord token configuration
- **Missing dependencies**: Run `pip3 install -r requirements.txt`
- **Permission errors**: Verify Discord bot has required server permissions
- **Connection timeout**: Check internet connectivity and Discord API status

### Current State Issues
- **No code to run**: This is expected - repository is in initial state
- **Missing files**: Only basic repository files exist currently
- **Cannot build/test**: No source code or configuration files present yet

## Development Environment Requirements

### System Requirements
- Python 3.12+ (3.12.3 confirmed available)
- pip package manager (24.0 confirmed available)
- Git for version control
- Internet connection for Discord API access

### Future Requirements (When Development Begins)
- Discord Developer Portal access for bot token
- Test Discord server for development
- Database system (SQLite/PostgreSQL depending on implementation)
- Text editor or IDE with Python support

This repository is ready for Discord bot development but requires implementation of the actual bot code and configuration.