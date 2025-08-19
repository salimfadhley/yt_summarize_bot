import asyncio
import logging

from yt_summarize_bot.config import Database
from yt_summarize_bot.redis_client import RedisClient

log = logging.getLogger(__name__)


class MemoryStorage:
    def __init__(self) -> None:
        self.data: dict[str, list[str]] = {}

    async def is_inserted(self, var: str, id: str | int) -> bool:
        return str(id) in self.data.get(var, [])

    async def insert(self, var: str, id: str | int) -> bool:
        var = str(var)
        id = str(id)
        if var not in self.data:
            self.data[var] = []
        if id not in self.data[var]:
            self.data[var].append(id)
        return True

    async def fetch_all(self, var: str) -> list[str]:
        return self.data.get(var, []) or []

    async def delete(self, var: str, id: str | int) -> bool:
        var = str(var)
        id = str(id)
        if var in self.data and id in self.data[var]:
            self.data[var].remove(id)
        return True


# Initialize database based on environment variable
if Database.DATABASE_TYPE.lower() == "redis":
    try:
        db: RedisClient | MemoryStorage = RedisClient(
            host=Database.REDIS_HOST or "localhost",
            port=Database.REDIS_PORT or 6379,
            password=Database.REDIS_PASSWORD,
        )
        # Test Redis connection
        asyncio.get_event_loop().run_until_complete(db.fetch_all("test"))
        log.info("Connected to Redis database successfully")
    except (ConnectionError, TimeoutError, OSError) as e:
        log.warning("Failed to connect to Redis, falling back to memory storage: %s", e)
        db = MemoryStorage()
    except (ValueError, TypeError) as e:
        log.warning("Invalid Redis configuration, falling back to memory storage: %s", e)
        db = MemoryStorage()
else:
    log.info("Using memory storage (DATABASE_TYPE=%s)", Database.DATABASE_TYPE)
    db = MemoryStorage()
