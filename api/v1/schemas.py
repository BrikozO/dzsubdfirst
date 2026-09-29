from pydantic import AliasChoices, BaseModel, Field

from domain.models.players import PLAYER_ID_PATTERN, NewPlayer


class LevelChangeRequest(BaseModel):
    delta: int = Field(description="На сколько изменить уровень (может быть отрицательным)")


class BatchCreateRequest(BaseModel):
    players: list[NewPlayer] = Field(min_length=1, max_length=10_000)


class ScoreRequest(BaseModel):
    player_id: str = Field(pattern=PLAYER_ID_PATTERN, validation_alias=AliasChoices("player_id", "playerId"))
    score: float = Field(description="Сколько очков прибавить (ZINCRBY)")


class ScoreResponse(BaseModel):
    player_id: str
    score: float


class AchievementRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=64,
        validation_alias=AliasChoices("name", "achievement", "achievement_name"),
    )


class AchievementAddResponse(BaseModel):
    player_id: str
    achievement: str
    added: bool  # False — достижение уже было


class AchievementCheckResponse(BaseModel):
    player_id: str
    achievement: str
    has: bool


class AchievementsResponse(BaseModel):
    player_id: str
    achievements: list[str]


class CommonAchievementsResponse(BaseModel):
    player_ids: tuple[str, str]
    common: list[str]
