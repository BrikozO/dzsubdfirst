from redis.asyncio import Redis
from redis.exceptions import ConnectionError, TimeoutError

from domain.dao.health import HealthDAO
from infra.redis.client import RedisClients
from infra.redis.errors import translate_redis_errors


@translate_redis_errors
class RedisHealthDAO(HealthDAO):
    """PING узлов и топология по версии Sentinel."""

    def __init__(self, clients: RedisClients):
        self._clients = clients

    async def ping_master(self) -> bool:
        return await self._ping(self._clients.master)

    async def ping_replica(self) -> bool:
        return await self._ping(self._clients.replica)

    async def master_address(self) -> str | None:
        try:
            host, port = await self._clients.master_address()
        except (ConnectionError, TimeoutError):
            return None
        return f"{host}:{port}"

    async def replica_addresses(self) -> list[str]:
        try:
            return [f"{host}:{port}" for host, port in await self._clients.replica_addresses()]
        except (ConnectionError, TimeoutError):
            return []

    @staticmethod
    async def _ping(client: Redis) -> bool:
        try:
            return bool(await client.ping())
        except (ConnectionError, TimeoutError):
            return False
