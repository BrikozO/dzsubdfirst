from abc import ABC, abstractmethod
from datetime import datetime

from domain.models.players import NewPlayer, Player, PlayerCreate


class PlayersDAO(ABC):
    """Профили игроков и их кеш."""

    @abstractmethod
    async def exists(self, player_id: str) -> bool: ...

    @abstractmethod
    async def upsert(self, player_id: str, data: PlayerCreate, created_at: datetime) -> None:
        """Создать/обновить профиль; created_at ставится только при первом создании."""

    @abstractmethod
    async def get(self, player_id: str) -> Player | None: ...

    @abstractmethod
    async def incr_level(self, player_id: str, delta: int) -> int:
        """Изменить уровень на delta, вернуть новый уровень."""

    @abstractmethod
    async def create_many(self, players: list[NewPlayer], created_at: datetime) -> None:
        """Массовая загрузка профилей одной пачкой."""

    @abstractmethod
    async def get_cached(self, player_id: str) -> Player | None: ...

    @abstractmethod
    async def set_cache(self, player: Player) -> None: ...

    @abstractmethod
    async def invalidate_cache(self, player_id: str) -> None: ...
