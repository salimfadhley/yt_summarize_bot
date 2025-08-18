# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Video Summarizer Bot - A Telegram bot that summarizes YouTube videos by extracting captions or transcribing audio, then using AI to generate concise summaries.

## Environment Setup

### Environment Files
- **`.env.example`** - Template with all available configuration options (committed to git)
- **`.env`** - Actual configuration with credentials (gitignored, never commit this)
- Configuration is loaded via `python-dotenv` in `config.py`

### Required Credentials (Bot won't start without these):
- `BOT_TOKEN` - Telegram bot token from [@BotFather](https://t.me/botfather)
- `AUTH_USER_ID` - Your Telegram user ID from [@userinfobot](https://t.me/userinfobot)

### Optional Configuration:
- `AI_API_KEY` - OpenAI-compatible API key (defaults to free Pollinations AI service)
- `AI_MODEL_NAME` - Model name (default: gemini-2.0-flash)
- `AI_API_URL` - API endpoint (default: https://text.pollinations.ai/openai)
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` - Redis configuration (falls back to in-memory storage)

### Setting Up Environment
```bash
# Create .env from template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

## Quick Start for Local Development

```bash
# 1. Clone and enter the project
git clone <repo-url> && cd yt_summarize_bot

# 2. Run automated setup (installs Poetry, dependencies, pre-commit hooks)
./setup.sh

# 3. Configure credentials
nano .env  # Add BOT_TOKEN and AUTH_USER_ID

# 4. Run the bot
make run
```

## Development Commands

### Makefile Overview

The project includes a comprehensive `Makefile` that standardizes all development workflows. This ensures consistent development practices across different environments and developers.

**Key Benefits:**
- Single command for complex multi-step operations
- Consistent commands across all developers
- Built-in dependency checking
- Automatic error handling

**Most Used Commands:**
- `make dev` - Complete setup from scratch (clean install)
- `make run` - Run the bot with environment checking
- `make format` - Auto-format all code
- `make test` - Run full test suite
- `make help` - See all available commands

### Local Development Setup

#### Automated Setup
```bash
# Full automated setup (recommended)
./setup.sh

# Or using Make
make dev         # Full dev setup from scratch
make setup       # Install deps + pre-commit hooks
make install     # Just install dependencies
```

#### Manual Poetry Setup
```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Install pre-commit hooks
poetry run pre-commit install

# Add new dependency
poetry add package-name

# Run the bot (multiple ways)
poetry run python -m yt_summarize_bot
# or
poetry run yt-summarize-bot
# or
make run
# or
./run.sh
```

#### Make Commands
```bash
make help        # Show all available commands
make dev         # Full development setup
make run         # Run the bot
make test        # Run tests
make lint        # Run linting
make format      # Format code with black
make typecheck   # Run mypy type checking
make precommit   # Run all pre-commit hooks
make security    # Run security scan with bandit
make clean       # Clean up cache and build files
make update      # Update all dependencies
```

### Docker Setup

#### Production
```bash
# Build and run with Docker Compose
docker compose up -d --build

# View logs
docker compose logs -f bot

# Stop services
docker compose down
```

#### Development (with dev tools)
```bash
# Build and run development container
docker compose -f docker-compose.dev.yaml up -d --build

# Run tests in container
docker compose -f docker-compose.dev.yaml run --rm bot poetry run pytest

# Run linting in container
docker compose -f docker-compose.dev.yaml run --rm bot poetry run black .
docker compose -f docker-compose.dev.yaml run --rm bot poetry run ruff check .

# Run type checking in container
docker compose -f docker-compose.dev.yaml run --rm bot poetry run mypy .

# Access container shell for debugging
docker compose -f docker-compose.dev.yaml exec bot /bin/bash
```

### Development Tools
```bash
# Format code
poetry run black .

# Lint code
poetry run ruff check .

# Type checking
poetry run mypy .

# Run tests
poetry run pytest

# Run all pre-commit hooks manually
poetry run pre-commit run --all-files

# Update pre-commit hooks
poetry run pre-commit autoupdate
```

## Architecture

### Package Structure

```
yt_summarize_bot/
├── __init__.py        # Package initialization
├── __main__.py        # Module entry point
├── main.py           # Core bot logic and handlers
├── config.py         # Configuration management
└── database.py       # Storage abstraction layer
```

### Core Components

1. **yt_summarize_bot/main.py** - Entry point with Telegram bot handlers and core logic:
   - `/start` - Welcome message
   - `/users` - Admin command to view user count
   - `/bcast` - Admin command to broadcast messages
   - YouTube URL handler - Processes video links for summarization

2. **yt_summarize_bot/config.py** - Configuration management using environment variables
   - `Telegram` class - Bot token and admin ID
   - `Ai` class - AI API configuration
   - `Database` class - Redis connection settings

3. **yt_summarize_bot/database.py** - Storage abstraction with fallback:
   - Primary: `RedisClient` for persistent storage
   - Fallback: `MemoryStorage` for in-memory storage when Redis unavailable

### Processing Flow

1. User sends YouTube URL to bot
2. Bot attempts caption extraction via yt-dlp
3. If no captions, downloads audio and transcribes using Pollinations AI audio API
4. Sends transcript to LLM (Pollinations AI or configured OpenAI-compatible API)
5. Returns formatted summary using Telegram markdown

## CI/CD and Quality Assurance

### GitHub Actions Workflows

The project includes automated CI/CD pipelines:

1. **Code Quality** (runs on every commit):
   - Black code formatting check
   - Ruff linting
   - MyPy type checking
   - YAML validation
   - Bandit security scanning

2. **CI Pipeline** (runs on main/develop branches):
   - Full test suite
   - Docker build verification
   - Multi-stage Docker testing

3. **Dependabot Integration**:
   - Automatic dependency updates
   - Auto-merge for passing updates
   - Weekly schedule for Python, GitHub Actions, and Docker

### Local Quality Checks

All GitHub Actions checks can be run locally:
```bash
make format      # Black formatting
make lint        # Ruff linting  
make typecheck   # MyPy type checking
make security    # Bandit security scan
make precommit   # All pre-commit hooks
```

### Key Dependencies

- `aiogram` - Telegram bot framework
- `yt-dlp` - YouTube content extraction (replaces pytube)
- `aiohttp` - Async HTTP requests for AI APIs
- `redis` - Optional persistent storage
- APIs: Pollinations AI (free fallback) or any OpenAI-compatible endpoint
