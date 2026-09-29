from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: str  # ok | degraded
    master: str | None  # адрес текущего мастера по версии Sentinel
    replicas: list[str]
    master_ping: bool
    replica_ping: bool
