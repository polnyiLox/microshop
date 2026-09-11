# Catalog Service

Сервис каталога и товарных остатков MicroShop. Хранит карточки товаров,
атомарно резервирует остатки и участвует в оформлении заказа через RabbitMQ.

## Ответственность

- CRUD карточек товаров;
- проверка доступного количества;
- атомарное резервирование нескольких позиций;
- возврат остатка при отмене заказа;
- загрузка и замена изображений товара в S3-совместимом хранилище;
- публикация результата inventory-команд.

Уменьшение остатка выполняется одним SQL `UPDATE` с условием
`quantity >= requested_quantity`, поэтому параллельные запросы не могут
зарезервировать больше товара, чем доступно.

## Архитектура

```text
app/
├── api/             # HTTP endpoints каталога
├── broker/          # RabbitMQ consumer, publisher и topology
├── cache/           # контракт кэша и Redis-клиент
├── core/s3_client.py # технический клиент MinIO/S3
├── db/models/       # модель Product
├── repositories/    # операции PostgreSQL
├── schemas/         # Product DTO
├── services/        # ProductService и InventoryService
└── main.py          # FastAPI lifespan и consumer
```

Сервис не содержит CORS middleware. Публичные запросы проходят через API
Gateway; внутренние inventory endpoints и broker-команды не предназначены
для прямого вызова браузером.

## HTTP API

Маршруты имеют префикс `/v1/products`:

- `GET /` и `GET /{product_id}`;
- `POST /`, `PATCH /{product_id}`, `DELETE /{product_id}`;
- `PUT /{product_id}/image` — загрузка JPEG, PNG или WebP;
- `POST /{product_id}/reserve`;
- `POST /{product_id}/release`;
- `GET /health` — состояние приложения.

Gateway оставляет чтение каталога публичным, а изменение товаров разрешает
только роли `seller`.

Swagger при development-запуске: <http://localhost:8001/docs>.

## Redis

`GET /v1/products/{product_id}` использует простой паттерн cache-aside:

1. `ProductService` ищет товар в Redis;
2. при промахе читает его через `ProductRepository` из PostgreSQL;
3. сохраняет JSON товара в Redis на 60 секунд;
4. после изменения товара или остатка удаляет устаревший ключ.

Repository по-прежнему отвечает только за PostgreSQL. Решение об использовании
и инвалидировании кэша принимает service-слой, а `RedisCache` содержит только
технические Redis-команды. Если Redis недоступен, чтение продолжает работать
через PostgreSQL.

## RabbitMQ

- команды: exchange `catalog.commands`, queue `catalog.order.queue`;
- routing keys: `inventory.reserve`, `inventory.release`, `inventory.confirm`;
- результаты публикуются в exchange `catalog.events`;
- события: `inventory.reserved`, `inventory.reservation_failed`,
  `inventory.released`, `inventory.release_failed`.

## Запуск всего проекта

```powershell
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build
```

Команда выполняется из корня репозитория. Контейнер `catalog-migrate`
применяет Alembic-миграции до запуска API.

## Локальная разработка

```powershell
Copy-Item .env.example .env
uv sync --frozen
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Для локального режима укажите в `.env` доступные адреса PostgreSQL, RabbitMQ,
Redis и MinIO.

## Тесты

```powershell
uv run pytest -q
```

Интеграционные и e2e-тесты PostgreSQL используют Testcontainers.

## CI/CD

GitHub Actions workflow находится в `.github/workflows/ci-cd.yaml`.

При создании или обновлении pull request в `master` workflow:

1. поднимает Python 3.14;
2. устанавливает `uv` и зависимости из зафиксированного `uv.lock`;
3. запускает весь набор тестов.

После push в `master` успешно протестированная версия дополнительно собирается
в Docker-образ и публикуется в GitHub Container Registry:

```text
ghcr.io/<github-owner>/catalog-service:latest
ghcr.io/<github-owner>/catalog-service:sha-<commit>
```

Тег с SHA однозначно связывает образ с Git-коммитом. Workflow использует
автоматический `GITHUB_TOKEN`; отдельный пароль GHCR не требуется.
