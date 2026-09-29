from abc import ABC, abstractmethod

# (id сообщения, поля); поля = None, если сообщение из pending уже удалено из очереди
QueueEntry = tuple[str, dict[str, str] | None]


class NotificationsDAO(ABC):
    """Очередь уведомлений с группой потребителей."""

    @abstractmethod
    async def ensure_group(self) -> bool:
        """Создать группу потребителей. False — группа уже была."""

    @abstractmethod
    async def add(self, fields: dict[str, str]) -> str:
        """Добавить сообщение, вернуть его id."""

    @abstractmethod
    async def read_group(
        self,
        consumer: str,
        *,
        pending: bool = False,
        count: int = 10,
        block_ms: int | None = None,
    ) -> list[QueueEntry]:
        """pending=True — свои неподтверждённые сообщения, иначе новые (с ожиданием до block_ms)."""

    @abstractmethod
    async def ack(self, *entry_ids: str) -> int: ...

    @abstractmethod
    async def length(self) -> int: ...
