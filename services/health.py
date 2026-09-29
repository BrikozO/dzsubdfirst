from domain.dao.health import HealthDAO
from domain.models.health import HealthStatus


class HealthService:
    def __init__(self, health: HealthDAO):
        self._health = health

    async def check(self) -> HealthStatus:
        master_ping = await self._health.ping_master()
        replica_ping = await self._health.ping_replica()
        master = await self._health.master_address()

        return HealthStatus(
            status="ok" if master_ping and replica_ping and master else "degraded",
            master=master,
            replicas=await self._health.replica_addresses(),
            master_ping=master_ping,
            replica_ping=replica_ping,
        )
