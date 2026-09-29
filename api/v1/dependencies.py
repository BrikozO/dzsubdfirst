from typing import Annotated

from fastapi import Depends, Path, Request

from domain.models.players import PLAYER_ID_PATTERN
from services.achievements import AchievementsService
from services.auth import AuthService
from services.container import Services
from services.health import HealthService
from services.leaderboards import LeaderboardService
from services.players import PlayerService


def get_services(request: Request) -> Services:
    # Контейнер собирается в lifespan (main.py)
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services)]


def get_player_service(services: ServicesDep) -> PlayerService:
    return services.players


def get_auth_service(services: ServicesDep) -> AuthService:
    return services.auth


def get_leaderboard_service(services: ServicesDep) -> LeaderboardService:
    return services.leaderboard


def get_achievements_service(services: ServicesDep) -> AchievementsService:
    return services.achievements


def get_health_service(services: ServicesDep) -> HealthService:
    return services.health


PlayerServiceDep = Annotated[PlayerService, Depends(get_player_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
LeaderboardServiceDep = Annotated[LeaderboardService, Depends(get_leaderboard_service)]
AchievementsServiceDep = Annotated[AchievementsService, Depends(get_achievements_service)]
HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]

PlayerId = Annotated[str, Path(pattern=PLAYER_ID_PATTERN, description="id игрока")]
