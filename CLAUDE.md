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

## Development Commands

### Poetry Setup
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

### Key Dependencies

- `aiogram` - Telegram bot framework
- `yt-dlp` - YouTube content extraction (replaces pytube)
- `aiohttp` - Async HTTP requests for AI APIs
- `redis` - Optional persistent storage
- APIs: Pollinations AI (free fallback) or any OpenAI-compatible endpoint