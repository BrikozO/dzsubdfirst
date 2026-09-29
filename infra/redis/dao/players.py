from datetime import datetime

from redis.asyncio import Redis

from domain.dao.players import PlayersDAO
from domain.models.players import NewPlayer, Player, PlayerCreate
from infra.redis.errors import translate_redis_errors

CACHE_TTL_SECONDS = 60


def player_key(player_id: str) -> str:
    return f"player:{player_id}"


def cache_key(player_id: str) -> str:
    return f"cache:player:{player_id}"


@translate_redis_errors
class RedisPlayersDAO(PlayersDAO):
    """Профили игроков (Hash player:{id}) и их кеш (String cache:player:{id}).

    Работает только с мастером: профиль читается сразу после записи,
    а кеш-aside при промахе сам пишет в Redis.
    """

    def __init__(self, master: Redis):
        self._master = master

    async def exists(self, player_id: str) -> bool:
        return bool(await self._master.exists(player_key(player_id)))

    async def upsert(self, player_id: str, data: PlayerCreate, created_at: datetime) -> None:
        key = player_key(player_id)
        # MULTI/EXEC: поля профиля обновляются вместе, created_at ставится только при первом создании
        async with self._master.pipeline(transaction=True) as pipe:
            pipe.hset(key, mapping=data.model_dump())
            pipe.hsetnx(key, "created_at", created_at.isoformat())
            await pipe.execute()

    async def get(self, player_id: str) -> Player | None:
        data = await self._master.hgetall(player_key(player_id))
        if not data:
            return None
        return Player(id=player_id, **data)

    async def incr_level(self, player_id: str, delta: int) -> int:
        return await self._master.hincrby(player_key(player_id), "level", delta)

    async def create_many(self, players: list[NewPlayer], created_at: datetime) -> None:
        """Массовая загрузка: все команды уходят одной пачкой через pipeline, без ожидания ответа на каждую."""
        async with self._master.pipeline(transaction=False) as pipe:
            for player in players:
                fields = player.model_dump(exclude={"id"}) | {"created_at": created_at.isoformat()}
                pipe.hset(player_key(player.id), mapping=fields)
                # профиль мог уже лежать в кеше — сбрасываем, чтобы не отдавать старые данные
                pipe.delete(cache_key(player.id))
            await pipe.execute()

    async def get_cached(self, player_id: str) -> Player | None:
        raw = await self._master.get(cache_key(player_id))
        if raw is None:
            return None
        return Player.model_validate_json(raw)

    async def set_cache(self, player: Player) -> None:
        await self._master.set(cache_key(player.id), player.model_dump_json(), ex=CACHE_TTL_SECONDS)

    async def invalidate_cache(self, player_id: str) -> None:
        await self._master.delete(cache_key(player_id))
