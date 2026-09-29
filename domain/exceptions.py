class DomainError(Exception):
    """Базовая ошибка предметной области."""


class NotFoundError(DomainError):
    pass


class PlayerNotFound(NotFoundError):
    def __init__(self, player_id: str):
        super().__init__(f"Игрок {player_id!r} не найден")
        self.player_id = player_id


class PlayerNotInLeaderboard(NotFoundError):
    def __init__(self, player_id: str):
        super().__init__(f"Игрока {player_id!r} нет в лидерборде")
        self.player_id = player_id


class StorageError(DomainError):
    """Хранилище не смогло выполнить операцию. Реализации DAO переводят в неё свои ошибки."""


class StorageUnavailable(StorageError):
    """Хранилище недоступно: сеть, таймаут, переключение мастера."""


class WriteRejected(StorageError):
    """Хранилище отказалось принять запись (например, нет живых реплик)."""
