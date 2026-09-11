# Order Service

Сервис заказов MicroShop. Хранит заказы и их позиции, координирует
резервирование товара и платежи, публикует события для уведомлений и аналитики.

## Ответственность

- создание и редактирование пользовательских заказов;
- проверка принадлежности заказа по доверенному `X-User-ID`;
- получение карточек товаров через catalog HTTP client;
- orchestration inventory и payment-команд через RabbitMQ;
- переходы между статусами заказа;
- публикация аналитических событий в Kafka.

## Архитектура

```text
app/
├── api/             # endpoints и ownership dependencies
├── broker/          # RabbitMQ и Kafka adapters
├── cache/           # cache-aside и ключи Redis
├── clients/         # HTTP client каталога
├── db/models/       # Order и OrderItem
├── repositories/    # операции PostgreSQL
├── schemas/         # команды, ответы и analytics events
├── services/        # бизнес-процесс заказа
└── main.py          # lifespan брокеров и consumer
```

Сервис не содержит CORS middleware. Внешний клиент работает через API Gateway,
который проверяет JWT и заменяет входящие identity headers доверенными claims.

## HTTP API

Маршруты имеют префикс `/v1/orders`:

- `GET /`, `POST /`, `GET /{order_id}`;
- `POST /{order_id}/cancel`, `POST /{order_id}/close`;
- CRUD позиций через `/{order_id}/items`;
- `PATCH /{order_id}` — внутреннее изменение статуса, не публикуется Gateway;
- `GET /health` — состояние приложения.

Swagger при development-запуске: <http://localhost:8002/docs>.

## Событийное взаимодействие

RabbitMQ:

- публикует команды в `catalog.commands` и `payment.commands`;
- получает inventory-события через queue `order.catalog.queue`;
- получает payment-события через queue `order.payment.queue`;
- публикует `order.created` и `order.cancelled` в `order.events`.

Kafka:

- публикует аналитику в `order.analytics.events`.

Названия exchange, queue и routing key централизованы в `app/core/config.py`.

## Запуск всего проекта

```powershell
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build
```

Команда выполняется из корня репозитория. `order-migrate` применяет миграции,
а API стартует после готовности catalog-service, RabbitMQ и Kafka.

## Локальная разработка

```powershell
Copy-Item .env.example .env
uv sync --frozen
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

В `.env` должны быть доступны PostgreSQL, catalog-service, RabbitMQ, Kafka и
Redis.

## Тесты

```powershell
uv run pytest -q
```

Интеграционные и e2e-тесты PostgreSQL используют Testcontainers.

## CI/CD

Workflow `.github/workflows/ci-cd.yaml` запускает тесты для pull request и push
в `master`. После успешного push публикуются образы
`ghcr.io/<github-owner>/order-service:latest` и `:sha-<commit>`.
