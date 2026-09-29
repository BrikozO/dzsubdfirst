from redis.asyncio import Redis

from domain.dao.leaderboards import LeaderboardDAO
from domain.models.leaderboards import LeaderboardEntry, PlayerRank
from infra.redis.errors import translate_redis_errors

TOURNAMENT_KEY = "tournament:main"


@translate_redis_errors
class RedisLeaderboardDAO(LeaderboardDAO):
    """Лидерборд турнира (Sorted Set tournament:main: member = player_id, score = очки).

    Запись — в мастер, чтение — с реплик.
    """

    def __init__(self, master: Redis, replica: Redis):
        self._master = master
        self._replica = replica

    async def add_score(self, player_id: str, score: float) -> float:
        """Прибавляет очки игроку, возвращает его новый счёт."""
        return await self._master.zincrby(TOURNAMENT_KEY, score, player_id)

    async def top(self, limit: int) -> list[LeaderboardEntry]:
        rows = await self._replica.zrevrange(TOURNAMENT_KEY, 0, limit - 1, withscores=True)
        return [
            LeaderboardEntry(rank=position, player_id=player_id, score=score)
            for position, (player_id, score) in enumerate(rows, start=1)
        ]

    async def rank(self, player_id: str) -> PlayerRank | None:
        # ZREVRANK, а не ZRANK: место считаем от наибольшего счёта, как и в топе (ZREVRANGE).
        # WITHSCORE (Redis 7.2+) сразу возвращает и счёт игрока.
        result = await self._replica.zrevrank(TOURNAMENT_KEY, player_id, withscore=True)
        if result is None:
            return None
        rank, score = result
        return PlayerRank(player_id=player_id, rank=rank + 1, score=score)
