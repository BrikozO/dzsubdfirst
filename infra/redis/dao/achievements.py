from redis.asyncio import Redis

from domain.dao.achievements import AchievementsDAO
from infra.redis.errors import translate_redis_errors


def achievements_key(player_id: str) -> str:
    return f"achievements:{player_id}"


@translate_redis_errors
class RedisAchievementsDAO(AchievementsDAO):
    """Достижения игрока (Set achievements:{id}). Запись — в мастер, чтение — с реплик."""

    def __init__(self, master: Redis, replica: Redis):
        self._master = master
        self._replica = replica

    async def add(self, player_id: str, achievement: str) -> bool:
        """True — достижение новое, False — уже было."""
        return bool(await self._master.sadd(achievements_key(player_id), achievement))

    async def has(self, player_id: str, achievement: str) -> bool:
        return bool(await self._replica.sismember(achievements_key(player_id), achievement))

    async def members(self, player_id: str) -> set[str]:
        return await self._replica.smembers(achievements_key(player_id))

    async def common(self, player_id: str, other_player_id: str) -> set[str]:
        return await self._replica.sinter(achievements_key(player_id), achievements_key(other_player_id))
