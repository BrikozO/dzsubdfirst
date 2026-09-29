from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Читаются из переменных окружения (и .env, если есть)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GameHub"
    log_level: str = "INFO"

    # Список Sentinel-ов в формате "host:port,host:port,..."
    redis_sentinels: str = "localhost:26379,localhost:26380,localhost:26381"
    redis_master_name: str = "mymaster"

    # Таймауты (секунды)
    redis_socket_timeout: float = 2.0
    redis_connect_timeout: float = 2.0
    redis_health_check_interval: int = 10

    # Ретраи на ConnectionError/TimeoutError: экспоненциальный backoff base * 2^n, но не больше cap
    redis_retries: int = 6
    # Чтения с реплик ретраим мало: зависшая реплика не должна держать запрос десятки секунд,
    # следующий запрос заново спросит у Sentinel живые реплики (или уйдёт на мастер)
    redis_replica_retries: int = 1
    redis_backoff_base: float = 0.2
    redis_backoff_cap: float = 3.0

    # Проверка соединения при старте
    redis_startup_attempts: int = 10
    redis_startup_delay: float = 2.0

    @property
    def sentinel_addresses(self) -> list[tuple[str, int]]:
        addresses = []
        for item in self.redis_sentinels.split(","):
            host, port = item.strip().rsplit(":", 1)
            addresses.append((host, int(port)))
        return addresses


@lru_cache
def get_settings() -> Settings:
    return Settings()
