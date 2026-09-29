from fastapi import APIRouter

from api.v1.dependencies import HealthServiceDep
from domain.models.health import HealthStatus

router = APIRouter(tags=["system"])


@router.get("/health")
async def health(service: HealthServiceDep) -> HealthStatus:
    """PING мастера и реплики + текущий мастер по версии Sentinel (удобно смотреть failover)."""
    return await service.check()
