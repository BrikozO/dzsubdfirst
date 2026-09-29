from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from api import basic_router
from domain.exceptions import NotFoundError, StorageError, WriteRejected
from infra.logger import setup_logging
from infra.redis.client import check_connection, create_redis_clients
from infra.redis.dao import create_redis_daos
from infra.settings import get_settings
from services.container import build_services

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    clients = create_redis_clients(settings)
    await check_connection(clients, settings.redis_startup_attempts, settings.redis_startup_delay)

    # Точка сборки: абстрактные DAO из domain получают Redis-реализации из infra
    services = build_services(create_redis_daos(clients))
    # XGROUP CREATE notifications notifications-group $ MKSTREAM — это запись, без реплик мастер её отклонит
    try:
        await services.notifications.ensure_group()
    except WriteRejected as exc:
        logger.warning("Группу потребителей создать не удалось (её создаст консьюмер при старте): {}", exc)
    app.state.services = services
    logger.success("{} запущен", settings.app_name)

    yield

    await clients.close()
    logger.info("Соединения с Redis закрыты")


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(basic_router)


@app.exception_handler(NotFoundError)
async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


@app.exception_handler(StorageError)
async def storage_error_handler(_: Request, exc: StorageError) -> JSONResponse:
    # Хранилище недоступно или не принимает записи (failover, split-brain) — временная проблема, клиент может повторить
    logger.error("{}: {}", type(exc).__name__, exc)
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": str(exc)})
