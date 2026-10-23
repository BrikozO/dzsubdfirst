# GameHub — бэкенд на Redis (ДЗ «Неделя 3»)

REST API для игровой платформы: профили игроков, счётчик входов, лидерборд турнира, достижения и очередь уведомлений.
Redis — единственное хранилище. Приложение работает с ним только через Sentinel.

## Запуск

```bash
docker compose up -d --build        # кластер Redis + приложение
docker compose ps                   # все контейнеры должны быть Up
docker exec redis-master redis-cli INFO replication   # connected_slaves:2 (на свежем кластере)
```

Роли узлов переживают перезапуск (см. [Конфигурация узлов](#конфигурация-узлов)). Чтобы начать с исходной топологии
(`redis-master` — мастер, остальные — его реплики), например перед записью демо, пересоздайте тома:

```bash
docker compose down -v && docker compose up -d --build
```

- API: http://localhost:8000, Swagger — http://localhost:8000/docs
- Redis Insight: http://localhost:5540

### Режим разработки (compose watch)

```bash
docker compose up --build --watch
```

Изменения кода синхронизируются в контейнер, и `uvicorn --reload` сам перезапускает приложение.
При изменении `pyproject.toml`, `uv.lock` или `Dockerfile` образ пересобирается.

## Архитектура

### Кластер

| Компонент | Контейнер | Порт | Назначение |
|---|---|---|---|
| Master | `redis-master` | 6379 | Записи. RDB + AOF, `maxmemory 256mb`, `volatile-lru`, `min-replicas-to-write 1` / `min-replicas-max-lag 10` (защита от split-brain) |
| Replica ×2 | `redis-replica-1/2` | 6380, 6381 | Чтения, `replica-read-only yes` |
| Sentinel ×3 | `redis-sentinel-1/2/3` | 26379–26381 | Мониторинг `mymaster`, кворум 2, автоматический failover |
| App | `gamehub-app` | 8000 | FastAPI, подключение через Sentinel |

Роли в таблице — исходные. После failover мастером может стать любой узел, а `redis-master` вернётся репликой.
Текущий мастер: `docker exec redis-sentinel-1 redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster`.

### Конфигурация узлов

```
conf/
  redis.conf            общий шаблон для всех Redis-узлов (персистентность, maxmemory, min-replicas-*)
  redis-entrypoint.sh   запуск Redis-узла: сборка конфига при первом старте, дальше им владеет Sentinel
  sentinel.conf         шаблон Sentinel: monitor mymaster redis-master 6379 2, resolve/announce-hostnames
```

Главный принцип: **исходная топология задаётся один раз, при первом запуске, а дальше ролями узлов управляет Sentinel.**
Если прописать `--replicaof redis-master 6379` в команде запуска, узел после любого перезапуска снова пойдёт реплицировать
контейнер `redis-master`, даже если тот уже не мастер. А исходный мастер, у которого в команде нет `replicaof`,
после перезапуска поднимется вторым мастером — это воспроизводилось при проверке.

Что делает `conf/redis-entrypoint.sh` при каждом старте узла:

1. **Первый запуск** (в томе ещё нет `/data/redis.conf`): копирует шаблон `conf/redis.conf` и дописывает
   - `replica-announce-ip $REDIS_ANNOUNCE_HOST` — под этим именем мастер показывает узел в `INFO replication`,
     а Sentinel его запоминает. Так все узлы известны по стабильным именам сервисов (`redis-master`, `replica-1`, `replica-2`),
     без IP контейнеров и без дублей после failover;
   - `replicaof $REDIS_REPLICAOF` — только у исходных реплик.
2. **Удаляет строки `loadmodule`** из конфига. Модули Redis 8 (JSON, Search и др.) подключает entrypoint образа
   при каждом старте, а `CONFIG REWRITE` сохраняет их в конфиг. Без чистки модуль загрузится дважды и Redis не стартует.
3. **Отдаёт конфиг пользователю `redis`**: Redis должен уметь его читать и переписывать.
4. **Выставляет `SKIP_FIX_PERMS=1`**: entrypoint образа не пытается чинить права в `/data`
   (и не пишет `Notice: Unknown file './redis.conf'`). Том создаётся из образа уже с владельцем `redis`.
5. **Запускает `docker-entrypoint.sh redis-server /data/redis.conf`** — стандартный entrypoint образа:
   он сбрасывает права до пользователя `redis` и подключает модули.

Переменные окружения узлов задаются в `docker-compose.yml`:

| Сервис | `REDIS_ANNOUNCE_HOST` | `REDIS_REPLICAOF` |
|---|---|---|
| `redis-master` | `redis-master` | — |
| `replica-1` | `replica-1` | `redis-master 6379` |
| `replica-2` | `replica-2` | `redis-master 6379` |

После failover Sentinel переназначает роли командами `REPLICAOF` + `CONFIG REWRITE`, и конфиг в томе обновляется.
Перезапущенный узел поднимается с последней назначенной ролью. Если исходный мастер остановили, пока он был мастером,
он на несколько секунд поднимется мастером, после чего Sentinel переведёт его в реплики. Записей на него в это время нет:
приложение ходит через Sentinel, а без реплик узел отклонит запись из-за `min-replicas-to-write`.

Sentinel-ы копируют шаблон `conf/sentinel.conf` в `/data/sentinel.conf` тоже только при первом запуске и хранят его
на своих томах (`sentinel-1/2/3-data`). Так перезапуск Sentinel не затирает текущего мастера и эпоху.

Правки `conf/redis.conf` и `conf/sentinel.conf` попадают только в новые тома — применяются через
`docker compose down -v && docker compose up -d`.

### Подключение приложения

Клиент мастера (`master_for`) используется для записей и чтений, где важна согласованность (профиль и его кеш).
Клиент реплик (`slave_for`) используется для чтения лидерборда и достижений. Если живых реплик нет, redis-py откатывается на мастер.
На сетевые ошибки настроены таймауты и ретраи с экспоненциальной задержкой: во время failover клиент дожидается нового мастера.
При старте приложение проверяет соединение с мастером и ждёт подключения реплик.

### Слои приложения

```
api/            HTTP: роутеры api/v1/* собираются в basic_router (prefix /api) в api/__init__.py
services/       бизнес-логика: кеш-aside, инвалидация, уведомления, pipeline; зависит только от абстракций domain
domain/
  dao/          абстрактные DAO (ABC): players, auth, leaderboards, achievements, notifications, health
  models/       pydantic-модели предметной области
  exceptions.py доменные ошибки: NotFoundError, StorageUnavailable, WriteRejected
infra/
  settings.py   настройки из переменных окружения
  logger.py     цветной loguru, перехват логов uvicorn
  redis/        клиенты через Sentinel + Redis-реализации DAO (infra/redis/dao)
main.py         сборка приложения: Redis-DAO -> сервисы -> FastAPI, обработчики доменных ошибок
scripts/        консьюмер уведомлений
seed/           players.json — 20 профилей для POST /api/players/batch
```

Redis-реализации DAO переводят ошибки redis-py в доменные: `StorageUnavailable` (сеть, таймаут) и `WriteRejected` (`NOREPLICAS`, `READONLY`).
API отвечает на них кодом 503.

## Данные в Redis

| Данные | Тип | Ключ | Поля / значение | TTL |
|---|---|---|---|---|
| Профиль игрока | Hash | `player:{id}` | `name`, `level`, `region`, `created_at` | ∞ |
| Счётчик входов | String | `logins:{id}` | число входов | 24 ч с первого входа |
| Кеш профиля | String | `cache:player:{id}` | JSON профиля | 60 с |
| Лидерборд | Sorted Set | `tournament:main` | member = `player_id`, score = очки | ∞ |
| Достижения | Set | `achievements:{id}` | названия достижений | ∞ |
| Уведомления | Stream | `notifications` | `player_id`, `type`, `message`, `timestamp` | 7 дней (`XADD ... MINID ~`) |

Группа потребителей `notifications-group` создаётся при старте (`XGROUP CREATE notifications notifications-group $ MKSTREAM`).

## API

| Метод | Путь | Тело | Операции в Redis |
|---|---|---|---|
| POST | `/api/players/{id}` | `{"name", "level", "region"}` | `EXISTS`, `MULTI HSET + HSETNX created_at EXEC`, `DEL cache:player:{id}`, `XADD` → 201 создан / 200 обновлён |
| GET | `/api/players/{id}` | — | `GET cache:player:{id}`, при промахе `HGETALL` + `SET ... EX 60`; заголовок `X-Cache: HIT/MISS` |
| PATCH | `/api/players/{id}/level` | `{"delta": 1}` | `HINCRBY player:{id} level {delta}`, `DEL cache:player:{id}`, `XADD` |
| POST | `/api/players/{id}/login` | — | Lua: `INCR logins:{id}` + `EXPIRE 86400` при первом входе |
| POST | `/api/players/batch` | `{"players": [{"id", "name", "level", "region"}, ...]}` (пример — `seed/players.json`) | pipeline из `HSET` (+ `DEL` кеша); в ответе `elapsed_ms` |
| POST | `/api/leaderboard/score` | `{"player_id", "score"}` | `ZINCRBY tournament:main {score} {player_id}` |
| GET | `/api/leaderboard/top?limit=10` | — | `ZREVRANGE tournament:main 0 9 WITHSCORES` |
| GET | `/api/leaderboard/rank/{id}` | — | `ZREVRANK tournament:main {id} WITHSCORE` (место с 1, от лучшего счёта) |
| POST | `/api/players/{id}/achievements` | `{"name"}` | `SADD achievements:{id} {name}` |
| GET | `/api/players/{id}/achievements` | — | `SMEMBERS achievements:{id}` |
| GET | `/api/players/{id}/achievements/{name}` | — | `SISMEMBER achievements:{id} {name}` |
| GET | `/api/players/{id1}/achievements/common/{id2}` | — | `SINTER achievements:{id1} achievements:{id2}` |
| GET | `/api/health` | — | `PING` мастера и реплики, текущий мастер и реплики по данным Sentinel |

Для места в лидерборде используется `ZREVRANK`, а не `ZRANK`: `ZRANK` считает от наименьшего счёта, а топ строится через `ZREVRANGE`.

## Консьюмер уведомлений

```bash
docker compose exec app python -m scripts.consume_notifications          # слушать поток (Ctrl+C — выход)
docker compose exec app python -m scripts.consume_notifications --once   # прочитать всё, что есть, и выйти
```

Консьюмер сначала дочитывает свои неподтверждённые сообщения (`XREADGROUP ... 0`), затем ждёт новые (`XREADGROUP ... BLOCK ... >`).
Каждое сообщение выводится в консоль и подтверждается `XACK`. Во время failover консьюмер переподключается сам.
Запускать его нужно внутри docker-сети: Sentinel отдаёт имена узлов из неё (`redis-master`, `replica-1`, `replica-2`), с хоста они не резолвятся.

## Сценарии демонстрации

Команды ниже рассчитаны на свежий кластер (`docker compose down -v && docker compose up -d --build`):
до failover мастер — `redis-master`. Split-brain удобнее показывать до failover.

```bash
API=http://localhost:8000/api
J='Content-Type: application/json'

# Профиль, кеш, уровень, уведомления
curl -X POST $API/players/1 -H "$J" -d '{"name":"Alice","level":3,"region":"eu"}'
curl -i $API/players/1                     # X-Cache: MISS
curl -i $API/players/1                     # X-Cache: HIT
docker exec redis-master redis-cli TTL cache:player:1          # > 0
curl -X PATCH $API/players/1/level -H "$J" -d '{"delta":2}'
docker exec redis-master redis-cli XLEN notifications          # > 0
docker compose exec app python -m scripts.consume_notifications --once

# Входы
curl -X POST $API/players/1/login
docker exec redis-master redis-cli GET logins:1

# Лидерборд и достижения
curl -X POST $API/leaderboard/score -H "$J" -d '{"player_id":"1","score":100}'
curl "$API/leaderboard/top?limit=10"
curl $API/leaderboard/rank/1
curl -X POST $API/players/1/achievements -H "$J" -d '{"name":"first_blood"}'
curl $API/players/1/achievements/first_blood
curl $API/players/1/achievements/common/2

# Pipeline: 20 профилей из сида одной пачкой
curl -X POST $API/players/batch -H "$J" -d @seed/players.json

# Failover
docker stop redis-master
sleep 15
docker exec redis-sentinel-1 redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster
curl $API/health                            # новый мастер, приложение работает
docker start redis-master                   # вернётся репликой нового мастера
docker exec redis-master redis-cli INFO replication   # role:slave, master_host:replica-1 или replica-2

# Split-brain: мастер без реплик отклоняет записи
docker pause redis-replica-1 redis-replica-2    # после failover — ставьте на паузу текущие реплики
sleep 12                                         # min-replicas-max-lag 10
curl -i -X POST $API/players/2 -H "$J" -d '{"name":"Bob","level":1,"region":"na"}'   # 503, NOREPLICAS
docker unpause redis-replica-1 redis-replica-2
```

## Настройки приложения (переменные окружения)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `REDIS_SENTINELS` | `localhost:26379,localhost:26380,localhost:26381` | адреса Sentinel |
| `REDIS_MASTER_NAME` | `mymaster` | имя мастера в Sentinel |
| `REDIS_SOCKET_TIMEOUT` / `REDIS_CONNECT_TIMEOUT` | `2.0` | таймауты, с |
| `REDIS_RETRIES` | `6` | ретраи клиента мастера (хватает, чтобы пережить failover) |
| `REDIS_REPLICA_RETRIES` | `1` | ретраи клиента реплик (зависшая реплика не держит запрос) |
| `REDIS_BACKOFF_BASE` / `REDIS_BACKOFF_CAP` | `0.2` / `3.0` | экспоненциальная задержка между ретраями, с |
| `LOG_LEVEL` | `INFO` | уровень логов |
