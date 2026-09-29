from datetime import UTC, datetime

from loguru import logger
from pydantic import ValidationError

from domain.dao.notifications import NotificationsDAO, QueueEntry
from domain.models.notifications import Notification, NotificationType, ReceivedNotification


class NotificationService:
    def __init__(self, notifications: NotificationsDAO):
        self._notifications = notifications

    async def ensure_group(self) -> None:
        if await self._notifications.ensure_group():
            logger.info("Создана группа потребителей для потока уведомлений")

    async def publish(self, player_id: str, type_: NotificationType, message: str) -> str:
        notification = Notification(
            player_id=player_id,
            type=type_,
            message=message,
            timestamp=datetime.now(UTC),
        )
        entry_id = await self._notifications.add(notification.to_stream_fields())
        logger.debug("XADD notifications {} -> {}", entry_id, notification.model_dump(mode="json"))
        return entry_id

    async def read_pending(self, consumer: str, count: int) -> list[ReceivedNotification]:
        entries = await self._notifications.read_group(consumer, pending=True, count=count)
        return [self._parse(entry) for entry in entries]

    async def read_new(self, consumer: str, count: int, block_ms: int) -> list[ReceivedNotification]:
        entries = await self._notifications.read_group(consumer, count=count, block_ms=block_ms)
        return [self._parse(entry) for entry in entries]

    async def ack(self, *entry_ids: str) -> int:
        return await self._notifications.ack(*entry_ids)

    async def stream_length(self) -> int:
        return await self._notifications.length()

    @staticmethod
    def _parse(entry: QueueEntry) -> ReceivedNotification:
        entry_id, fields = entry
        if fields is None:
            return ReceivedNotification(id=entry_id, notification=None, raw=None)
        try:
            notification = Notification.model_validate(fields)
        except ValidationError:
            notification = None
        return ReceivedNotification(id=entry_id, notification=notification, raw=fields)
