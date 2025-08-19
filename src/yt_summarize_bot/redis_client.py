import logging

from redis.asyncio import Redis

log = logging.getLogger(__name__)


class RedisClient:
    def __init__(self, host: str, port: int, password: str | None) -> None:
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
