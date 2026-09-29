from abc import ABC, abstractmethod

from domain.models.leaderboards import LeaderboardEntry, PlayerRank


class LeaderboardDAO(ABC):
    """Лидерборд турнира."""

    @abstractmethod
    async def add_score(self, player_id: str, score: float) -> float:
        """Прибавить очки игроку, вернуть его новый счёт."""

    @abstractmethod
    async def top(self, limit: int) -> list[LeaderboardEntry]: ...

    @abstractmethod
    async def rank(self, player_id: str) -> PlayerRank | None:
        """Место игрока (1 — наибольший счёт) или None, если его нет в лидерборде."""
