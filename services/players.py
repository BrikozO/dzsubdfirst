import time
from datetime import UTC, datetime

from loguru import logger

from domain.dao.players import PlayersDAO
from domain.exceptions import PlayerNotFound
from domain.models.notifications import NotificationType
from domain.models.players import BatchCreateResult, NewPlayer, Player, PlayerCreate
from services.notifications import NotificationService


class PlayerService:
    def __init__(self, players: PlayersDAO, notifications: NotificationService):
        self._players = players
        self._notifications = notifications

    async def upsert(self, player_id: str, data: PlayerCreate) -> tuple[Player, bool]:
        """Создаёт или обновляет профиль. Возвращает (профиль, создан ли он только что)."""
        created = not await self._players.exists(player_id)
        await self._players.upsert(player_id, data, created_at=datetime.now(UTC))
        await self._players.invalidate_cache(player_id)
        player = await self._get_or_raise(player_id)

        if created:
            await self._notifications.publish(
                player_id, NotificationType.PROFILE_CREATED, f"Создан профиль игрока {player.name}"
            )
        else:
            await self._notifications.publish(
                player_id, NotificationType.PROFILE_UPDATED, f"Профиль игрока {player.name} обновлён"
            )
        logger.info("Профиль {} {}", player_id, "создан" if created else "обновлён")
        return player, created

    async def get(self, player_id: str) -> tuple[Player, bool]:
        """Cache-aside. Возвращает (профиль, попали ли в кеш)."""
        cached = await self._players.get_cached(player_id)
        if cached is not None:
            logger.info("Кеш профиля {}: HIT", player_id)
            return cached, True

        logger.info("Кеш профиля {}: MISS — читаем Hash и кладём в кеш", player_id)
        player = await self._get_or_raise(player_id)
        await self._players.set_cache(player)
        return player, False

    async def change_level(self, player_id: str, delta: int) -> Player:
        # Без проверки HINCRBY создал бы «профиль» из одного поля level
        if not await self._players.exists(player_id):
            raise PlayerNotFound(player_id)

        new_level = await self._players.incr_level(player_id, delta)
        await self._players.invalidate_cache(player_id)
        await self._notifications.publish(
            player_id,
            NotificationType.LEVEL_CHANGED,
            f"Уровень изменён на {delta:+d}, теперь {new_level}",
        )
        logger.info("Уровень игрока {}: {:+d} -> {}", player_id, delta, new_level)
        return await self._get_or_raise(player_id)

    async def create_batch(self, players: list[NewPlayer]) -> BatchCreateResult:
        started = time.perf_counter()
        await self._players.create_many(players, created_at=datetime.now(UTC))
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        logger.info("Pipeline: загружено {} профилей за {} мс", len(players), elapsed_ms)
        return BatchCreateResult(created=len(players), elapsed_ms=elapsed_ms)

    async def _get_or_raise(self, player_id: str) -> Player:
        player = await self._players.get(player_id)
        if player is None:
            raise PlayerNotFound(player_id)
        return player
