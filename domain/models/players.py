from datetime import datetime

from pydantic import BaseModel, Field

# id игрока попадает в ключи Redis (player:{id}), поэтому без ":" и пробелов
PLAYER_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class PlayerCreate(BaseModel):
    """Данные профиля, которые присылает клиент."""

    name: str = Field(min_length=1, max_length=64)
    level: int = Field(default=1, ge=0)
    region: str = Field(min_length=1, max_length=32)


class NewPlayer(PlayerCreate):
    """Профиль вместе с id — для массовой загрузки."""

    id: str = Field(pattern=PLAYER_ID_PATTERN)


class Player(PlayerCreate):
    """Профиль игрока, как он лежит в Hash player:{id}."""

    id: str
    created_at: datetime


class BatchCreateResult(BaseModel):
    created: int
    elapsed_ms: float
