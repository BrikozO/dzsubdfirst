from fastapi import APIRouter

from api.v1 import v1_router

# Код версионируется пакетами (api/v1, api/v2, ...), а URL — как в контракте ДЗ: /api/...
basic_router = APIRouter(prefix="/api")
basic_router.include_router(v1_router)
