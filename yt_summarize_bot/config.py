import logging
import os
import sys

from dotenv import load_dotenv

from yt_summarize_bot.exceptions import MissingConfigurationError

load_dotenv()

log = logging.getLogger(__name__)


def _get_required_env_var(var_name: str, description: str, example: str) -> str:
    """Get a required environment variable with helpful error message."""
    value = os.environ.get(var_name)
    if not value:
        print(f"ERROR: Missing required environment variable: {var_name}")
        print(f"Description: {description}")
        print(f"Example: {example}")
        print()
        print("How to fix this:")
        print("1. Create a .env file in your project root (if it doesn't exist)")
        print("2. Add the following line to your .env file:")
        print(f"   {var_name}={example}")
        print()
        print("For detailed setup instructions, see:")
        print("   - README.md (Prerequisites section)")
        print("   - .env.example (template file)")
        print()
        raise MissingConfigurationError(var_name)
    return value


def _get_optional_env_var(var_name: str, default: str, description: str = "") -> str:
    """Get an optional environment variable with default value."""
    value = os.environ.get(var_name, default)
    if not value and description:
        print(f"INFO: Using default for {var_name} - {description}")
    return value


class Telegram:
    BOT_TOKEN = _get_required_env_var(
        "BOT_TOKEN",
        "Telegram Bot API token from @BotFather",
        "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    )

    _auth_user_id_str = _get_required_env_var(
        "AUTH_USER_ID",
        "Your Telegram user ID for admin commands (get from @userinfobot)",
        "123456789",
    )

    try:
        AUTH_USER_ID = int(_auth_user_id_str)
    except ValueError:
        print(f"ERROR: AUTH_USER_ID must be a number, got: {_auth_user_id_str}")
        print("Get your user ID by messaging @userinfobot on Telegram")
        print("   It should be a number like: 123456789")
        sys.exit(1)


class Ai:
    API_KEY = os.environ.get("AI_API_KEY")
    MODEL_NAME = _get_optional_env_var("AI_MODEL_NAME", "gemini-2.0-flash")
    API_URL = _get_optional_env_var("AI_API_URL", "https://text.pollinations.ai/openai")


class Database:
    DATABASE_TYPE = _get_optional_env_var(
        "DATABASE_TYPE",
        "memory",
        "Database type: 'redis' for Redis, 'memory' for in-memory storage",
    )
    REDIS_HOST = os.environ.get("REDIS_HOST")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")
