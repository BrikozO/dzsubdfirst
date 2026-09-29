from abc import ABC, abstractmethod


class HealthDAO(ABC):
    """Состояние хранилища: доступность узлов и текущая топология."""

    @abstractmethod
    async def ping_master(self) -> bool: ...

    @abstractmethod
    async def ping_replica(self) -> bool: ...

    @abstractmethod
    async def master_address(self) -> str | None:
        """Адрес текущего мастера "host:port" или None, если его не удалось узнать."""

    @abstractmethod
    async def replica_addresses(self) -> list[str]: ...
