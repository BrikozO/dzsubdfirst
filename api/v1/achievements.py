from typing import Annotated

from fastapi import APIRouter, Path

from api.v1.dependencies import AchievementsServiceDep, PlayerId
from api.v1.schemas import (
    AchievementAddResponse,
    AchievementCheckResponse,
    AchievementRequest,
    AchievementsResponse,
    CommonAchievementsResponse,
)
from domain.models.players import PLAYER_ID_PATTERN

router = APIRouter(prefix="/players", tags=["achievements"])


@router.post("/{player_id}/achievements")
async def add_achievement(
    player_id: PlayerId,
    body: AchievementRequest,
    service: AchievementsServiceDep,
) -> AchievementAddResponse:
    """SADD achievements:{id} {name}."""
    added = await service.add(player_id, body.name)
    return AchievementAddResponse(player_id=player_id, achievement=body.name, added=added)


@router.get("/{player_id}/achievements")
async def list_achievements(player_id: PlayerId, service: AchievementsServiceDep) -> AchievementsResponse:
    """SMEMBERS achievements:{id} (с реплики)."""
    return AchievementsResponse(player_id=player_id, achievements=await service.list_all(player_id))


@router.get("/{player_id}/achievements/common/{other_id}")
async def common_achievements(
    player_id: PlayerId,
    other_id: Annotated[str, Path(pattern=PLAYER_ID_PATTERN, description="id второго игрока")],
    service: AchievementsServiceDep,
) -> CommonAchievementsResponse:
    """SINTER achievements:{id1} achievements:{id2} (с реплики)."""
    common = await service.common(player_id, other_id)
    return CommonAchievementsResponse(player_ids=(player_id, other_id), common=common)


@router.get("/{player_id}/achievements/{name}")
async def check_achievement(
    player_id: PlayerId,
    name: str,
    service: AchievementsServiceDep,
) -> AchievementCheckResponse:
    """SISMEMBER achievements:{id} {name} (с реплики)."""
    has = await service.has(player_id, name)
    return AchievementCheckResponse(player_id=player_id, achievement=name, has=has)
