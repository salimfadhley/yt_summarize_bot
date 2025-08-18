import asyncio


class MemoryStorage:
    def __init__(self):
        self.data = {}

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


try:
    from redis.asyncio import Redis

    from yt_summarize_bot.config import Database

    class RedisClient:
        def __init__(self, host: str, port: int, password: str | None):
            self.db = Redis(
                host=host,
                port=port,
                password=password,
                ssl=True if password else False,
                decode_responses=True,
            )

        def _s_l(self, text: str) -> list[str]:
            return text.split(" ") if text else []

        def _l_s(self, lst: list[str]) -> str:
            return " ".join(lst).strip()

        async def is_inserted(self, var: str, id: str | int) -> bool:
            users = await self.fetch_all(var)
            return str(id) in users

        async def insert(self, var: str, id: str | int) -> bool:
            var = str(var)
            id = str(id)
            users = await self.fetch_all(var)
            if id not in users:
                users.append(id)
                await self.db.set(var, self._l_s(users))
            return True

        async def fetch_all(self, var: str) -> list[str]:
            users = await self.db.get(var)
            return self._s_l(users) if users else []

        async def delete(self, var: str, id: str | int) -> bool:
            var = str(var)
            id = str(id)
            users = await self.fetch_all(var)
            if id in users:
                users.remove(id)
                await self.db.set(var, self._l_s(users))
            return True

    try:
        db: RedisClient | MemoryStorage = RedisClient(
            host=Database.REDIS_HOST or "localhost",
            port=Database.REDIS_PORT or 6379,
            password=Database.REDIS_PASSWORD,
        )
        asyncio.get_event_loop().run_until_complete(db.fetch_all("test"))
    except Exception:
        db = MemoryStorage()

except ImportError:
    db: RedisClient | MemoryStorage = MemoryStorage()  # type: ignore
