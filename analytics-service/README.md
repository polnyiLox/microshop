# Analytics Service

Сервис аналитики MicroShop. Получает события заказов и платежей из Kafka,
идемпотентно сохраняет их в MongoDB и строит агрегированные отчёты.

## Ответственность

- чтение топиков `order.analytics.events` и `payment.analytics.events`;
- проверка структуры событий через Pydantic;
- защита от повторной записи по `event_id`;
- расчёт метрик заказов, платежей, выручки и популярных товаров;
- кэширование общей сводки в Redis;
- управление Kafka consumer и MongoDB через FastAPI lifespan.

## Архитектура

```text
app/
├── api/             # HTTP endpoints и FastAPI dependencies
├── broker/          # Kafka client и consumer
├── cache/           # cache-aside для общей сводки
├── db/              # MongoDB client и индексы
├── repositories/    # запросы и aggregation pipelines MongoDB
├── schemas/         # входные события и ответы API
├── services/        # расчёт отчётов и обработка событий
└── main.py          # приложение и lifespan
```

API не настраивает CORS: браузер обращается к аналитике только через API
Gateway, где выполняются проверка JWT и проверка роли `admin`.

## HTTP API

Все маршруты имеют префикс `/v1/analytics`:

- `GET /overview` — сводные показатели;
- `GET /orders` — статистика заказов;
- `GET /payments` — статистика платежей;
- `GET /revenue` — выручка по периодам;
- `GET /products/top` — популярные товары;
- `GET /health` — состояние приложения.

Swagger при development-запуске: <http://localhost:8005/docs>.

## Запуск всего проекта

Из корня репозитория:

```powershell
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build
```

MongoDB, Kafka и настройки подключения передаются сервису общим Compose.

## Локальная разработка

```powershell
Copy-Item .env.example .env
uv sync --frozen
uv run uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

При локальном запуске укажите в `.env` доступные с компьютера адреса MongoDB,
Kafka и Redis вместо Docker DNS-имён.

## Тесты

```powershell
uv run pytest -q
```

Интеграционные и e2e-тесты используют MongoDB Testcontainer, поэтому требуют
запущенный Docker.

## CI/CD

Workflow `.github/workflows/ci-cd.yaml` запускает тесты для pull request и push
в `master`. После успешного push публикуются образы
`ghcr.io/<github-owner>/analytics-service:latest` и `:sha-<commit>`.
