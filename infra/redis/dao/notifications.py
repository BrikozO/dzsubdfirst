from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from domain.dao.notifications import NotificationsDAO, QueueEntry
from infra.redis.errors import translate_redis_errors

STREAM_KEY = "notifications"
GROUP_NAME = "notifications-group"
RETENTION = timedelta(days=7)


@translate_redis_errors
class RedisNotificationsDAO(NotificationsDAO):
    """Очередь уведомлений (Stream notifications + группа notifications-group).

    Всё только на мастере: XREADGROUP и XACK меняют состояние группы, это запись.
    """

    def __init__(self, master: Redis):
        self._master = master

    async def ensure_group(self) -> bool:
        """XGROUP CREATE notifications notifications-group $ MKSTREAM. False — группа уже была."""
        try:
            return await self._master.xgroup_create(STREAM_KEY, GROUP_NAME, id="$", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                return False
            raise

    async def add(self, fields: dict[str, str]) -> str:
        # Храним 7 дней: при каждом XADD отрезаем записи старше недели (MINID ~ <ms>-0).
        # id записи в потоке начинается с unix-времени в мс, поэтому MINID работает как TTL.
        min_id = int((datetime.now(UTC) - RETENTION).timestamp() * 1000)
        return await self._master.xadd(STREAM_KEY, fields, minid=f"{min_id}-0", approximate=True)

    async def read_group(
        self,
        consumer: str,
        *,
        pending: bool = False,
        count: int = 10,
        block_ms: int | None = None,
    ) -> list[QueueEntry]:
        """XREADGROUP: pending=True — свои неподтверждённые (id 0), иначе новые (id >)."""
        response = await self._master.xreadgroup(
            GROUP_NAME,
            consumer,
            {STREAM_KEY: "0" if pending else ">"},
            count=count,
            block=None if pending else block_ms,
        )
        if not response:
            return []
        # RESP2: [[stream, [(id, fields), ...]]]; RESP3: {stream: [[id, fields], ...]}
        if isinstance(response, dict):
            entries = response.get(STREAM_KEY, [])
        else:
            entries = response[0][1]
        return [(entry_id, fields) for entry_id, fields in entries]

    async def ack(self, *entry_ids: str) -> int:
        if not entry_ids:
            return 0
        return await self._master.xack(STREAM_KEY, GROUP_NAME, *entry_ids)

    async def length(self) -> int:
        return await self._master.xlen(STREAM_KEY)
