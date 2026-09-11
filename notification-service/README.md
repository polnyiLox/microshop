# Notification Service

Сервис уведомлений MicroShop. Преобразует события заказов и платежей в
пользовательские уведомления, сохраняет их в PostgreSQL и доставляет онлайн
через WebSocket.

## Ответственность

- получение событий `order.events` и `payment.events` из RabbitMQ;
- сохранение истории уведомлений;
- выдача только уведомлений текущего пользователя;
- доставка новых уведомлений по активным WebSocket-подключениям;
- управление соединениями и broker consumer через FastAPI lifespan.

## Архитектура

```text
app/
├── api/             # HTTP и WebSocket endpoints
├── broker/          # RabbitMQ topology и consumer
├── cache/           # cache-aside для списков уведомлений
├── db/models/       # модель Notification
├── repositories/    # операции PostgreSQL
├── services/        # создание и изменение уведомлений
├── websocket/       # connection manager
└── main.py          # FastAPI lifespan
```

Сервис не содержит CORS middleware. API Gateway проверяет access-токен,
подставляет доверенный `X-User-ID` и проксирует WebSocket без пользовательского
`user_id` во внешнем URL.

## HTTP и WebSocket API

- `GET /v1/notifications/users/{user_id}`;
- `GET /v1/notifications/{notification_id}`;
- `WS /v1/notifications/ws/{user_id}` — внутренний WebSocket route;
- `GET /health` — состояние приложения.

Публичное WebSocket-подключение выполняется через Gateway:

```javascript
const socket = new WebSocket(
  "ws://localhost:8080/v1/notifications/ws",
  ["bearer", accessToken],
);
```

Swagger при development-запуске: <http://localhost:8004/docs>.

## RabbitMQ

- queue `notification.order.queue` слушает `order.created` и
  `order.cancelled`;
- queue `notification.payment.queue` слушает `payment.succeeded`,
  `payment.failed`, `payment.cancelled` и `payment.refunded`.

## Запуск всего проекта

```powershell
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build
```

Команда выполняется из корня репозитория. Перед API запускается
`notification-migrate`.

## Локальная разработка

```powershell
Copy-Item .env.example .env
uv sync --frozen
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
```

Для локального режима укажите в `.env` адреса PostgreSQL, RabbitMQ и Redis.

## Тесты

```powershell
uv run pytest -q
```

Интеграционные и e2e-тесты PostgreSQL используют Testcontainers.

## CI/CD

Workflow `.github/workflows/ci-cd.yaml` запускает тесты для pull request и push
в `master`. После успешного push публикуются образы
`ghcr.io/<github-owner>/notification-service:latest` и `:sha-<commit>`.
