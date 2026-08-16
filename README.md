# AI Gateway

Прокси-сервер (API Gateway) перед сторонними ИИ-провайдерами (OpenAI, Anthropic, Gemini).
Каждый запрос проходит три шага:

1. **Проверка API-ключа** — ключ передаётся в заголовке `X-API-Key`, шлюз сверяет его
   SHA-256 хэш с таблицей `api_key` в **PostgreSQL** (сам ключ нигде не хранится в открытом виде).
2. **Rate limiting** — не более **5 запросов в минуту** на ключ (fixed-window счётчик в **Redis**,
   `INCR` + `EXPIRE`). При превышении — `429 Too Many Requests` с заголовком `Retry-After`.
   Лимит можно переопределить индивидуально для ключа.
3. **Проксирование** — запрос пересылается выбранному ИИ-провайдеру (`openai` / `anthropic` / `auto`
   с выбором по приоритету) и результат логируется в `request_log`.

## Стек

FastAPI, SQLAlchemy 2.0 (async, asyncpg), Alembic, Redis (`redis.asyncio`), aiohttp, Docker Compose.

## Быстрый старт

```bash
cp .env.example .env
docker compose up -d --build
```

Поднимаются три контейнера: `ai_gateway` (FastAPI), `db` (PostgreSQL), `redis` (Redis).
При старте `ai_gateway` дожидается готовности PostgreSQL и накатывает миграции (`alembic upgrade head`).
Контейнер `xray` — опциональный четвёртый, для обхода блокировок (см. ниже), по умолчанию не поднимается.

## Создание API-ключа

Ключи создаются через CLI (в контейнере или локально с доступом к БД):

```bash
docker compose exec ai_gateway python -m scripts.manage_keys create --name "client-a"
# Created key id=... name=client-a
# API key (shown once, store it securely): <RAW_KEY>

docker compose exec ai_gateway python -m scripts.manage_keys list
docker compose exec ai_gateway python -m scripts.manage_keys revoke <key_id>
```

Можно задать индивидуальный лимит: `--rate-limit 20`.

## Использование

```bash
curl -X POST http://localhost:8100/api/v1/complete \
  -H "X-API-Key: <RAW_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Привет!"}],
    "provider": "openai"
  }'
```

При превышении лимита (6-й запрос за минуту):

```
HTTP/1.1 429 Too Many Requests
Retry-After: 37

{"detail": "Rate limit exceeded: max 5 requests per minute"}
```

Проверка доступности провайдеров: `GET /api/v1/health`.

## Локальная разработка

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

docker compose up db redis -d
alembic upgrade head
uvicorn main:app --reload --port 8100
```

## Линтеры

```bash
black .            # автоформатирование
black --check .    # проверка без изменений (то, что гоняет CI)
flake8 .
```

На каждый `push`/`pull_request` GitHub Actions (`.github/workflows/lint.yml`) прогоняет
`black --check .` и `flake8 .`.

## Обход блокировок (Xray / VLESS)

Если сервер хостится в регионе, откуда нет прямого доступа к OpenAI/Anthropic, шлюз может
ходить к ним через локальный SOCKS5-прокси (Xray с VLESS+Reality) вместо прямого подключения:

1. Впишите свои реальные VLESS-креды (адрес сервера, UUID, publicKey реальности) в `xray.json`
   — в репозитории лежит только шаблон с плейсхолдерами `REPLACE_WITH_...`, реальные секреты
   в git не коммитятся.
2. В `.env` выставьте `PROXY_ENABLED=true` (адрес прокси `PROXY_URL=socks5://xray:10808`
   уже настроен по умолчанию на контейнер `xray` из compose).
3. Запустите с профилем `proxy`, чтобы поднялся и контейнер Xray:
   ```bash
   docker compose --profile proxy up -d --build
   ```

Без `--profile proxy` контейнер `xray` не запускается — по умолчанию шлюз ходит к провайдерам
напрямую. Логика подключения — `_build_connector` в `app/gateways/base.py`: при
`PROXY_ENABLED=true` `aiohttp` использует `aiohttp-socks.ProxyConnector` с резолвом DNS
на стороне прокси (`rdns=True`), чтобы не светить DNS-запросы напрямую.

## Тесты

```bash
pytest -q
```

Тесты используют SQLite in-memory (вместо PostgreSQL) и `fakeredis` (вместо Redis) — реальные
сервисы для запуска тестов не нужны. `tests/test_rate_limiter.py` явно проверяет: 5 запросов
проходят, 6-й получает 429, лимит считается независимо на каждый ключ, и что индивидуальный
`rate_limit_per_minute` переопределяет дефолт.

## Структура

```
app/
  settings.py        # конфигурация (.env)
  security.py         # verify_api_key — проверка ключа в PostgreSQL
  rate_limiter.py      # rate_limit — счётчик в Redis, 429 при превышении
  router.py            # LLMRouter — выбор провайдера / приоритеты
  dependencies.py       # сборка гейтвеев из настроек
  db/
    models.py           # ApiKey, RequestLog
    repositories.py
  gateways/
    base.py, openai_gateway.py, anthropic_gateway.py, gemini_gateway.py, retry.py
  routers/llm.py        # POST /complete, GET /health
migrations/              # Alembic
scripts/manage_keys.py    # CLI создания/отзыва ключей
tests/
main.py                    # точка входа FastAPI
```

## Лицензия

[Apache License 2.0](LICENSE). При распространении копии или производной работы
обязательно сохранить копирайт и файл [NOTICE](NOTICE) с указанием автора.
