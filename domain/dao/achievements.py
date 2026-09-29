from abc import ABC, abstractmethod


class AchievementsDAO(ABC):
    """Уникальные достижения игроков."""

    @abstractmethod
    async def add(self, player_id: str, achievement: str) -> bool:
        """True — достижение новое, False — уже было."""

    @abstractmethod
    async def has(self, player_id: str, achievement: str) -> bool: ...

    @abstractmethod
    async def members(self, player_id: str) -> set[str]: ...

    @abstractmethod
    async def common(self, player_id: str, other_player_id: str) -> set[str]: ...
