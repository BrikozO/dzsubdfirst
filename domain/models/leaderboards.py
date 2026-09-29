from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int  # место, начиная с 1
    player_id: str
    score: float


class PlayerRank(BaseModel):
    player_id: str
    rank: int  # место, начиная с 1 (1 — наибольший счёт)
    score: float
