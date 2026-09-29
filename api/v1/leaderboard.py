from typing import Annotated

from fastapi import APIRouter, Query

from api.v1.dependencies import LeaderboardServiceDep, PlayerId
from api.v1.schemas import ScoreRequest, ScoreResponse
from domain.models.leaderboards import LeaderboardEntry, PlayerRank

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.post("/score")
async def add_score(body: ScoreRequest, service: LeaderboardServiceDep) -> ScoreResponse:
    """ZINCRBY tournament:main {score} {player_id}."""
    total = await service.add_score(body.player_id, body.score)
    return ScoreResponse(player_id=body.player_id, score=total)


@router.get("/top")
async def get_top(
    service: LeaderboardServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[LeaderboardEntry]:
    """ZREVRANGE tournament:main 0 {limit-1} WITHSCORES (с реплики)."""
    return await service.top(limit)


@router.get("/rank/{player_id}")
async def get_rank(player_id: PlayerId, service: LeaderboardServiceDep) -> PlayerRank:
    """Место игрока (1 — лучший): ZREVRANK tournament:main {player_id} WITHSCORE (с реплики)."""
    return await service.rank(player_id)
