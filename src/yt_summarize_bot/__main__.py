"""Entry point for running the bot as a module."""

import asyncio
import logging
import os
import sys
from datetime import datetime

log = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging for the application."""
    # Get log level from environment variable, default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler with daily rotation
            logging.FileHandler(
                f"{log_dir}/bot_{datetime.now().strftime('%Y-%m-%d')}.log", encoding="utf-8"
            ),
        ],
    )

    # Set specific loggers to appropriate levels
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    log.info("Logging configured successfully")
    log.info(f"Log level: {log_level}")


if __name__ == "__main__":
    setup_logging()
    log.info("Starting YouTube Summarizer Bot...")

    try:
        from yt_summarize_bot.main import main

        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped by user")
    except SystemExit:
        raise
