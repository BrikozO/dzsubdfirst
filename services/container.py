from dataclasses import dataclass

from domain.dao import DAOs
from services.achievements import AchievementsService
from services.auth import AuthService
from services.health import HealthService
from services.leaderboards import LeaderboardService
from services.notifications import NotificationService
from services.players import PlayerService


@dataclass
class Services:
    players: PlayerService
    auth: AuthService
    leaderboard: LeaderboardService
    achievements: AchievementsService
    notifications: NotificationService
    health: HealthService


def build_services(daos: DAOs) -> Services:
    """Собирает сервисы поверх абстрактных DAO — сервисы не знают, что внизу Redis."""
    notifications = NotificationService(daos.notifications)

    return Services(
        players=PlayerService(daos.players, notifications),
        auth=AuthService(daos.logins, daos.players),
        leaderboard=LeaderboardService(daos.leaderboard),
        achievements=AchievementsService(daos.achievements),
        notifications=notifications,
        health=HealthService(daos.health),
    )
