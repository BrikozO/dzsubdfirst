#!/bin/sh
# Запуск Redis-узла с конфигом, которым после первого старта владеет Sentinel.
#
# Конфиг узла лежит в его томе (/data/redis.conf) и создаётся из общего шаблона только при первом запуске.
# После failover Sentinel делает на узле REPLICAOF <новый мастер> + CONFIG REWRITE, поэтому при перезапуске
# узел поднимается с последней назначенной ролью, а не с исходной топологией.
# Вернуть исходную топологию: docker compose down -v
#
# Переменные окружения:
#   REDIS_ANNOUNCE_HOST — имя, под которым мастер и Sentinel видят этот узел (имя сервиса в compose)
#   REDIS_REPLICAOF     — "host port" мастера при первом запуске; у исходного мастера не задаётся
set -e

CONF=/data/redis.conf

if [ ! -f "$CONF" ]; then
    cp /usr/local/etc/redis/redis.conf "$CONF"
    echo "replica-announce-ip $REDIS_ANNOUNCE_HOST" >> "$CONF"
    if [ -n "$REDIS_REPLICAOF" ]; then
        echo "replicaof $REDIS_REPLICAOF" >> "$CONF"
    fi
fi

# Модули Redis 8 entrypoint образа подключает при каждом старте через --loadmodule, а CONFIG REWRITE
# сохраняет их в конфиг строками loadmodule. Без этой чистки модуль загрузится дважды и Redis не стартует
sed -i '/^loadmodule /d' "$CONF"
# Redis работает от пользователя redis и должен уметь читать и переписывать конфиг (CONFIG REWRITE)
chown redis:redis "$CONF"

# Entrypoint образа чинит права в /data, только если там лишь *.rdb и appendonlydir; из-за redis.conf он
# пропускает починку и пишет Notice "Unknown file". Починка не нужна: том создаётся из образа с владельцем redis,
# а владельца конфига выставили выше
export SKIP_FIX_PERMS=1

# Через стандартный entrypoint образа: он сбрасывает права до пользователя redis и подключает модули Redis 8
exec docker-entrypoint.sh redis-server "$CONF"
