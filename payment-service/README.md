# Payment Service

Сервис платежей MicroShop. Управляет жизненным циклом платежа, обрабатывает
команды order-service и публикует результаты для заказов, уведомлений и аналитики.

## Ответственность

- создание одного активного платежа на заказ;
- переходы `pending → processing → succeeded`;
- отмена ожидающего платежа;
- возврат успешного платежа;
- идемпотентная обработка повторного статуса;
- идемпотентное списание и зачисление средств через auth-service;
- повторная попытка оплаты после статуса `failed`;
- публикация событий в RabbitMQ и Kafka.

Текущая реализация демонстрационная: `complete` имитирует задержку внешнего
платёжного провайдера, реальный acquiring SDK не подключён.

## Архитектура

```text
app/
├── api/             # endpoints и ownership dependencies
├── broker/          # RabbitMQ consumer/publisher и Kafka producer
├── cache/           # cache-aside и ключи Redis
├── clients/         # внутренний HTTP client баланса
├── db/models/       # модель Payment
├── repositories/    # операции PostgreSQL
├── schemas/         # HTTP и event DTO
├── services/        # переходы статусов и публикация событий
└── main.py          # lifespan broker-клиентов
```

Сервис не содержит CORS middleware. API Gateway разрешает пользователю только
просмотр, завершение и отмену собственного платежа; создание платежа и
произвольный статус остаются внутренними операциями.

## HTTP API

Маршруты имеют префикс `/v1/payments`:

- `GET /?order_id=...` и `GET /{payment_id}`;
- `POST /{payment_id}/complete`;
- `POST /{payment_id}/cancel`;
- `POST /{payment_id}/retry`;
- `POST /` и `PATCH /{payment_id}/status` — внутренние endpoints;
- `GET /health` — состояние приложения.

Swagger при development-запуске: <http://localhost:8003/docs>.

## Событийное взаимодействие

RabbitMQ:

- queue `payment.order.queue` принимает `payment.create`, `payment.cancel` и
  `payment.refund` из exchange `payment.commands`;
- exchange `payment.events` публикует `payment.created`, `payment.succeeded`,
  `payment.failed`, `payment.cancelled` и `payment.refunded`.

Kafka:

- аналитические события публикуются в `payment.analytics.events`.

## Запуск всего проекта

```powershell
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build
```

Команда выполняется из корня репозитория. Перед API запускается
`payment-migrate`.

## Локальная разработка

```powershell
Copy-Item .env.example .env
uv sync --frozen
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

Для локального режима укажите в `.env` адреса PostgreSQL, RabbitMQ, Kafka,
Redis и внутреннего API auth-service.

## Тесты

```powershell
uv run pytest -q
```

Интеграционные и e2e-тесты PostgreSQL используют Testcontainers.

## CI/CD

Workflow `.github/workflows/ci-cd.yaml` запускает тесты для pull request и push
в `master`. После успешного push публикуются образы
`ghcr.io/<github-owner>/payment-service:latest` и `:sha-<commit>`.
