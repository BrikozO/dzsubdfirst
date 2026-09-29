from abc import ABC, abstractmethod


class LoginDAO(ABC):
    """Счётчик входов игрока за сутки."""

    @abstractmethod
    async def register_login(self, player_id: str) -> tuple[int, int]:
        """Атомарно учесть вход. Возвращает (количество входов, через сколько секунд счётчик сбросится)."""
