import inspect
from functools import wraps

from redis.exceptions import ConnectionError, ReadOnlyError, ResponseError, TimeoutError

from domain.exceptions import StorageUnavailable, WriteRejected


def _translate(method):
    @wraps(method)
    async def wrapper(*args, **kwargs):
        try:
            return await method(*args, **kwargs)
        except (ConnectionError, TimeoutError) as exc:
            # Сюда попадаем, когда ретраи клиента уже исчерпаны
            raise StorageUnavailable(f"Redis недоступен: {exc}") from exc
        except ReadOnlyError as exc:
            raise WriteRejected(f"Запись попала на реплику, идёт переключение мастера: {exc}") from exc
        except ResponseError as exc:
            if "NOREPLICAS" in str(exc):
                # min-replicas-to-write: мастер без живых реплик не принимает записи (защита от split-brain)
                raise WriteRejected(f"У мастера нет доступных реплик: {exc}") from exc
            raise

    return wrapper


def translate_redis_errors(cls):
    """Декоратор класса DAO: ошибки redis-py из публичных async-методов превращаются в доменные.

    Так слои выше (сервисы, API) не зависят от того, что внизу именно Redis.
    """
    for name, attr in list(vars(cls).items()):
        if not name.startswith("_") and inspect.iscoroutinefunction(attr):
            setattr(cls, name, _translate(attr))
    return cls
