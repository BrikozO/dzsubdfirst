import asyncio
from dataclasses import dataclass

from loguru import logger
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.asyncio.sentinel import Sentinel
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError

from infra.settings import Settings


@dataclass
class RedisClients:
    """Клиенты Redis, полученные через Sentinel.

    master  — все записи и чтения, где важна согласованность (read-your-writes).
    replica — чтения, которые допускают небольшое отставание репликации.
              Если живых реплик нет, redis-py сам откатывается на мастер.
    """

    sentinel: Sentinel
    master: Redis
    replica: Redis
    master_name: str

    async def master_address(self) -> tuple[str, int]:
        return await self.sentinel.discover_master(self.master_name)

    async def replica_addresses(self) -> list[tuple[str, int]]:
        return list(await self.sentinel.discover_slaves(self.master_name))

    async def close(self) -> None:
        await self.master.aclose()
        await self.replica.aclose()
        for sentinel_node in self.sentinel.sentinels:
            await sentinel_node.aclose()


def _retry(settings: Settings, retries: int) -> Retry:
    return Retry(
        ExponentialBackoff(cap=settings.redis_backoff_cap, base=settings.redis_backoff_base),
        retries=retries,
        supported_errors=(ConnectionError, TimeoutError),
    )


def create_redis_clients(settings: Settings) -> RedisClients:
    sentinel = Sentinel(
        settings.sentinel_addresses,
        sentinel_kwargs={
            "socket_timeout": settings.redis_socket_timeout,
            "socket_connect_timeout": settings.redis_connect_timeout,
            "decode_responses": True,
        },
        socket_timeout=settings.redis_socket_timeout,
        socket_connect_timeout=settings.redis_connect_timeout,
        health_check_interval=settings.redis_health_check_interval,
        decode_responses=True,
    )
    return RedisClients(
        sentinel=sentinel,
        # Во время failover соединение с мастером рвётся, а пул при переподключении
        # заново спрашивает у Sentinel адрес текущего мастера — ретраев хватает, чтобы его дождаться
        master=sentinel.master_for(settings.redis_master_name, retry=_retry(settings, settings.redis_retries)),
        replica=sentinel.slave_for(settings.redis_master_name, retry=_retry(settings, settings.redis_replica_retries)),
        master_name=settings.redis_master_name,
    )


async def check_connection(clients: RedisClients, attempts: int, delay: float) -> None:
    """Проверка соединения при старте.

    1. Ждём, пока Sentinel отдаст мастера и тот ответит на PING — без этого стартовать нельзя.
    2. Ждём, пока к мастеру подключится хотя бы одна реплика: из-за min-replicas-to-write 1
       без реплик мастер отклоняет записи. Если реплики так и не появились — стартуем с предупреждением
       (чтение работает, а запись заработает, как только реплики вернутся).
    """
    for attempt in range(1, attempts + 1):
        try:
            await clients.master.ping()
            host, port = await clients.master_address()
            logger.success("Redis доступен через Sentinel: master={}:{}", host, port)
            break
        except (ConnectionError, TimeoutError) as exc:
            logger.warning("Redis недоступен (попытка {}/{}): {}", attempt, attempts, exc)
            await asyncio.sleep(delay)
    else:
        raise RuntimeError(f"Не удалось подключиться к Redis за {attempts} попыток")

    for attempt in range(1, attempts + 1):
        replication = await clients.master.info("replication")
        connected = int(replication.get("connected_slaves", 0))
        if connected > 0:
            replicas = [f"{h}:{p}" for h, p in await clients.replica_addresses()]
            logger.success("К мастеру подключено реплик: {}, Sentinel видит: {}", connected, replicas)
            return
        logger.warning("К мастеру пока не подключены реплики (попытка {}/{})", attempt, attempts)
        await asyncio.sleep(delay)
    logger.warning("Реплик нет — мастер будет отклонять записи (min-replicas-to-write), пока они не вернутся")
