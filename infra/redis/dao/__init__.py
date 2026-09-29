from domain.dao import DAOs
from infra.redis.client import RedisClients
from infra.redis.dao.achievements import RedisAchievementsDAO
from infra.redis.dao.auth import RedisLoginDAO
from infra.redis.dao.health import RedisHealthDAO
from infra.redis.dao.leaderboards import RedisLeaderboardDAO
from infra.redis.dao.notifications import RedisNotificationsDAO
from infra.redis.dao.players import RedisPlayersDAO


def create_redis_daos(clients: RedisClients) -> DAOs:
    """Redis-реализации абстрактных DAO из domain.dao."""
    return DAOs(
        players=RedisPlayersDAO(clients.master),
        logins=RedisLoginDAO(clients.master),
        leaderboard=RedisLeaderboardDAO(clients.master, clients.replica),
        achievements=RedisAchievementsDAO(clients.master, clients.replica),
        notifications=RedisNotificationsDAO(clients.master),
        health=RedisHealthDAO(clients),
    )
