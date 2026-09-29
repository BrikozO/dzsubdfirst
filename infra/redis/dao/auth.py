from redis.asyncio import Redis

from domain.dao.auth import LoginDAO
from infra.redis.errors import translate_redis_errors

LOGINS_TTL_SECONDS = 24 * 60 * 60

# INCR и EXPIRE выполняются атомарно: между ними никто не вклинится,
# и ключ не останется без TTL, если клиент упадёт посередине.
# TTL ставится при первом входе за сутки (или если ключ почему-то оказался без TTL),
# поэтому счётчик показывает количество входов за 24 часа с первого входа.
REGISTER_LOGIN_LUA = """
local count = redis.call('INCR', KEYS[1])
if count == 1 or redis.call('TTL', KEYS[1]) < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {count, redis.call('TTL', KEYS[1])}
"""


def logins_key(player_id: str) -> str:
    return f"logins:{player_id}"


@translate_redis_errors
class RedisLoginDAO(LoginDAO):
    """Счётчик входов игрока за сутки (String logins:{id})."""

    def __init__(self, master: Redis):
        # register_script вызывает EVALSHA и сам делает SCRIPT LOAD при NOSCRIPT
        # (актуально после failover: у нового мастера кеш скриптов пустой)
        self._register_login = master.register_script(REGISTER_LOGIN_LUA)

    async def register_login(self, player_id: str) -> tuple[int, int]:
        """Возвращает (количество входов, TTL счётчика в секундах)."""
        count, ttl = await self._register_login(keys=[logins_key(player_id)], args=[LOGINS_TTL_SECONDS])
        return int(count), int(ttl)
