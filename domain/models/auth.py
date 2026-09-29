from pydantic import BaseModel


class LoginStats(BaseModel):
    player_id: str
    logins_today: int
    ttl_seconds: int  # через сколько счётчик logins:{id} сбросится
