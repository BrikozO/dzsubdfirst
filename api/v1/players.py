from fastapi import APIRouter, Response, status

from api.v1.dependencies import PlayerId, PlayerServiceDep
from api.v1.schemas import BatchCreateRequest, LevelChangeRequest
from domain.models.players import BatchCreateResult, Player, PlayerCreate

router = APIRouter(prefix="/players", tags=["players"])


# Объявлен раньше POST /{player_id}, иначе "batch" попадёт в player_id
@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def create_players_batch(body: BatchCreateRequest, service: PlayerServiceDep) -> BatchCreateResult:
    """Массовое создание профилей одной пачкой через pipeline (пример тела — seed/players.json)."""
    return await service.create_batch(body.players)


@router.post("/{player_id}")
async def upsert_player(
    player_id: PlayerId,
    body: PlayerCreate,
    response: Response,
    service: PlayerServiceDep,
) -> Player:
    """Создать/обновить профиль: HSET player:{id} + DEL cache:player:{id} + XADD notifications."""
    player, created = await service.upsert(player_id, body)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return player


@router.get("/{player_id}")
async def get_player(player_id: PlayerId, response: Response, service: PlayerServiceDep) -> Player:
    """Получить профиль через кеш (cache-aside, TTL 60 с). В заголовке X-Cache — HIT или MISS."""
    player, cache_hit = await service.get(player_id)
    response.headers["X-Cache"] = "HIT" if cache_hit else "MISS"
    return player


@router.patch("/{player_id}/level")
async def change_level(player_id: PlayerId, body: LevelChangeRequest, service: PlayerServiceDep) -> Player:
    """HINCRBY player:{id} level {delta} + DEL cache:player:{id} + XADD notifications."""
    return await service.change_level(player_id, body.delta)
