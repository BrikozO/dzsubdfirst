from loguru import logger

from domain.dao.leaderboards import LeaderboardDAO
from domain.exceptions import PlayerNotInLeaderboard
from domain.models.leaderboards import LeaderboardEntry, PlayerRank


class LeaderboardService:
    def __init__(self, leaderboard: LeaderboardDAO):
        self._leaderboard = leaderboard

    async def add_score(self, player_id: str, score: float) -> float:
        total = await self._leaderboard.add_score(player_id, score)
        logger.info("Лидерборд: игрок {} {:+g} очков, всего {:g}", player_id, score, total)
        return total

    async def top(self, limit: int) -> list[LeaderboardEntry]:
        return await self._leaderboard.top(limit)

    async def rank(self, player_id: str) -> PlayerRank:
        rank = await self._leaderboard.rank(player_id)
        if rank is None:
            raise PlayerNotInLeaderboard(player_id)
        return rank
