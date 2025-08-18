"""Entry point for running the bot as a module."""

import asyncio

from yt_summarize_bot.main import main

if __name__ == "__main__":
    asyncio.run(main())
