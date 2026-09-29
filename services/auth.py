from loguru import logger

from domain.dao.auth import LoginDAO
from domain.dao.players import PlayersDAO
from domain.exceptions import PlayerNotFound
from domain.models.auth import LoginStats


class AuthService:
    def __init__(self, logins: LoginDAO, players: PlayersDAO):
        self._logins = logins
        self._players = players

    async def login(self, player_id: str) -> LoginStats:
        if not await self._players.exists(player_id):
            raise PlayerNotFound(player_id)

        count, ttl = await self._logins.register_login(player_id)
        logger.info("Вход игрока {}: {} за сутки, сброс через {} с", player_id, count, ttl)
        return LoginStats(player_id=player_id, logins_today=count, ttl_seconds=ttl)
