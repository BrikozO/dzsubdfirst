from fastapi import APIRouter

from api.v1 import achievements, auth, leaderboard, players, system

v1_router = APIRouter()
# players первым: POST /players/batch должен матчиться раньше POST /players/{player_id}
v1_router.include_router(players.router)
v1_router.include_router(auth.router)
v1_router.include_router(achievements.router)
v1_router.include_router(leaderboard.router)
v1_router.include_router(system.router)
