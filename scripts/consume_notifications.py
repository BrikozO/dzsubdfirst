"""Потребитель уведомлений из Stream notifications.

Читает сообщения через XREADGROUP в группе notifications-group, выводит их в консоль и подтверждает XACK.
Сначала дочитывает свои неподтверждённые (pending) сообщения — например, после падения, — затем ждёт новые.

Запуск (внутри docker-сети, т.к. Sentinel отдаёт адреса узлов из неё):
    docker compose exec app python -m scripts.consume_notifications
    docker compose exec app python -m scripts.consume_notifications --once
"""

import argparse
import asyncio
import signal
import socket

from loguru import logger

from domain.exceptions import StorageError
from domain.models.notifications import ReceivedNotification
from infra.logger import setup_logging
from infra.redis.client import check_connection, create_redis_clients
from infra.redis.dao.notifications import RedisNotificationsDAO
from infra.settings import get_settings
from services.notifications import NotificationService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Потребитель уведомлений GameHub (Redis Streams)")
    parser.add_argument("--consumer", default=f"consumer-{socket.gethostname()}", help="имя потребителя в группе")
    parser.add_argument("--count", type=int, default=10, help="сколько сообщений читать за раз")
    parser.add_argument("--block-ms", type=int, default=5000, help="сколько ждать новых сообщений, мс")
    parser.add_argument("--once", action="store_true", help="прочитать всё, что есть, и выйти")
    return parser.parse_args()


def handle(message: ReceivedNotification) -> None:
    """«Обработка» уведомления — вывод в консоль."""
    n = message.notification
    if n is None:
        logger.warning("[{}] пропущено нечитаемое сообщение: {}", message.id, message.raw)
        return
    logger.opt(colors=True).info(
        "<magenta>[{}]</magenta> <yellow>{}</yellow> player=<cyan>{}</cyan>: {} <dim>({})</dim>",
        message.id,
        n.type,
        n.player_id,
        n.message,
        n.timestamp.isoformat(),
    )


async def process(service: NotificationService, messages: list[ReceivedNotification]) -> int:
    for message in messages:
        handle(message)
    # Подтверждаем и нечитаемые сообщения, иначе они навсегда застрянут в pending
    return await service.ack(*(message.id for message in messages))


async def consume(service: NotificationService, args: argparse.Namespace, stop: asyncio.Event) -> int:
    processed = 0

    # 1. Свои pending: сообщения, которые этот потребитель получил, но не успел подтвердить
    while pending := await service.read_pending(args.consumer, args.count):
        logger.info("Дочитываем pending: {} шт.", len(pending))
        processed += await process(service, pending)

    # 2. Новые сообщения
    while not stop.is_set():
        try:
            messages = await service.read_new(args.consumer, args.count, args.block_ms)
        except StorageError as exc:
            # Идёт failover или у мастера нет реплик: клиент сам найдёт нового мастера через Sentinel
            logger.warning("Хранилище недоступно, повтор через 1 с: {}", exc)
            await asyncio.sleep(1)
            continue

        if messages:
            processed += await process(service, messages)
        elif args.once:
            break
    return processed


async def main() -> None:
    args = parse_args()
    settings = get_settings()
    setup_logging(settings.log_level)

    # XREADGROUP BLOCK держит соединение открытым block_ms — таймаут сокета должен быть больше
    settings = settings.model_copy(
        update={"redis_socket_timeout": max(settings.redis_socket_timeout, args.block_ms / 1000 + 2)}
    )
    clients = create_redis_clients(settings)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    try:
        await check_connection(clients, settings.redis_startup_attempts, settings.redis_startup_delay)
        service = NotificationService(RedisNotificationsDAO(clients.master))
        await service.ensure_group()

        logger.info("Потребитель {!r} слушает поток notifications (Ctrl+C — выход)", args.consumer)
        processed = await consume(service, args, stop)
        logger.success(
            "Обработано и подтверждено сообщений: {}. Всего в потоке: {}",
            processed,
            await service.stream_length(),
        )
    finally:
        await clients.close()


if __name__ == "__main__":
    asyncio.run(main())
