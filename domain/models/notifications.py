from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class NotificationType(StrEnum):
    PROFILE_CREATED = "profile_created"
    PROFILE_UPDATED = "profile_updated"
    LEVEL_CHANGED = "level_changed"


class Notification(BaseModel):
    """Сообщение в Stream notifications: поля player_id, type, message, timestamp."""

    player_id: str
    # str, а не NotificationType: консьюмер должен уметь прочитать и типы, которых он не знает
    type: str
    message: str
    timestamp: datetime

    def to_stream_fields(self) -> dict[str, str]:
        return self.model_dump(mode="json")


class ReceivedNotification(BaseModel):
    """Сообщение, прочитанное из группы потребителей. notification=None — битое или удалённое сообщение."""

    id: str
    notification: Notification | None
    raw: dict[str, str] | None
