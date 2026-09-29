from fastapi import APIRouter

from api.v1.dependencies import AuthServiceDep, PlayerId
from domain.models.auth import LoginStats

router = APIRouter(prefix="/players", tags=["auth"])


@router.post("/{player_id}/login")
async def login(player_id: PlayerId, service: AuthServiceDep) -> LoginStats:
    """Зафиксировать вход: Lua-скрипт INCR logins:{id} + EXPIRE 86400."""
    return await service.login(player_id)
