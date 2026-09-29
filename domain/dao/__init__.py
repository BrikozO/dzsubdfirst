from dataclasses import dataclass

from domain.dao.achievements import AchievementsDAO
from domain.dao.auth import LoginDAO
from domain.dao.health import HealthDAO
from domain.dao.leaderboards import LeaderboardDAO
from domain.dao.notifications import NotificationsDAO
from domain.dao.players import PlayersDAO


@dataclass
class DAOs:
    """Набор DAO, из которого собираются сервисы. Реализации подставляются снаружи (infra)."""

    players: PlayersDAO
    logins: LoginDAO
    leaderboard: LeaderboardDAO
    achievements: AchievementsDAO
    notifications: NotificationsDAO
    health: HealthDAO
