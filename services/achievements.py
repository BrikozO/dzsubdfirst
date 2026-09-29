from loguru import logger

from domain.dao.achievements import AchievementsDAO


class AchievementsService:
    def __init__(self, achievements: AchievementsDAO):
        self._achievements = achievements

    async def add(self, player_id: str, achievement: str) -> bool:
        added = await self._achievements.add(player_id, achievement)
        logger.info("Достижение {!r} игрока {}: {}", achievement, player_id, "добавлено" if added else "уже было")
        return added

    async def has(self, player_id: str, achievement: str) -> bool:
        return await self._achievements.has(player_id, achievement)

    async def list_all(self, player_id: str) -> list[str]:
        return sorted(await self._achievements.members(player_id))

    async def common(self, player_id: str, other_player_id: str) -> list[str]:
        return sorted(await self._achievements.common(player_id, other_player_id))
