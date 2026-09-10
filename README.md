# MicroShop

Учебный marketplace, построенный как набор асинхронных микросервисов. Проект показывает слоистую архитектуру FastAPI-приложений, событийное взаимодействие, отдельные хранилища данных, кэширование, наблюдаемость и контейнерный запуск всей системы.

## Архитектура

| Компонент | Ответственность | Хранилище |
|---|---|---|
| [API Gateway](api-gateway/) | JWT-проверка, роли, маршрутизация HTTP и WebSocket | — |
| [Auth service](auth-service/) | пользователи, refresh-токены, роли и баланс | PostgreSQL |
| [Catalog service](catalog-service/) | товары, остатки и изображения в S3 | PostgreSQL, MinIO |
| [Order service](order-service/) | заказы и жизненный цикл заказа | PostgreSQL |
| [Payment service](payment-service/) | списание, возврат и статусы платежей | PostgreSQL |
| [Notification service](notification-service/) | уведомления и доставка по WebSocket | PostgreSQL |
| [Analytics service](analytics-service/) | обработка событий и аналитические отчёты | MongoDB |
| [Frontend](frontend/) | интерфейсы покупателя, продавца и администратора | — |

Внутри доменных сервисов соблюдается направление зависимостей `API → Service → Repository → DB`. Синхронные запросы проходят через HTTP, команды и доменные события — через RabbitMQ, аналитические события — через Kafka. Redis используется как необязательный кэш: при его недоступности сервисы продолжают читать данные из основной БД.

## Технологии

- Python, FastAPI, Pydantic, SQLAlchemy и Alembic;
- PostgreSQL и MongoDB;
- RabbitMQ и Kafka;
- Redis и MinIO (S3 API);
- Docker Compose;
- Prometheus, Grafana, Loki и Grafana Alloy;
- Pytest, Testcontainers и GitHub Actions.

## Быстрый запуск

Понадобятся Docker Desktop, Docker Compose и OpenSSL.

Сгенерируйте локальную пару JWT-ключей. Приватный ключ остаётся только в
`auth-service` и исключён из Git, а Gateway получает только публичный ключ:

```powershell
New-Item -ItemType Directory -Force auth-service/certs | Out-Null
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out auth-service/certs/jwt-private.pem
openssl pkey -in auth-service/certs/jwt-private.pem -pubout -out auth-service/certs/jwt-public.pem
Copy-Item auth-service/certs/jwt-public.pem api-gateway/certs/jwt-public.pem -Force
```

Затем создайте локальный файл с секретами:

```powershell
Copy-Item .env.example .env
```

Замените все значения `change-this-*` в `.env`. Файл исключён из Git. Затем запустите систему:

```powershell
docker compose up --build
```

После успешного запуска доступны:

- frontend — <http://localhost:3000>;
- API Gateway — <http://localhost:8080>;
- OpenAPI Gateway — <http://localhost:8080/docs> (proxy-маршруты намеренно скрыты);
- Grafana — <http://localhost:3001>;
- Prometheus — <http://localhost:9090>;
- Grafana Alloy — <http://localhost:12345>;
- MinIO API и Console — <http://localhost:9000> и <http://localhost:9001>.

Compose ждёт готовность инфраструктуры, запускает Alembic-миграции и только после них поднимает API. В обычном режиме доменные API и базы не публикуют порты на хост.

## Режим разработки

Чтобы открыть Swagger каждого сервиса и инфраструктурные порты, примените override-файл:

```powershell
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build
```

Swagger будет доступен на портах:

- auth — <http://localhost:8000/docs>;
- catalog — <http://localhost:8001/docs>;
- order — <http://localhost:8002/docs>;
- payment — <http://localhost:8003/docs>;
- notification — <http://localhost:8004/docs>;
- analytics — <http://localhost:8005/docs>.

RabbitMQ Management UI публикуется на `15672`, Kafka — на `9092`, MongoDB — на `27017`, PostgreSQL сервисов — на `54320`–`54324`.

## Тесты

В сервисах разделены три уровня проверок:

- unit — бизнес-правила и адаптеры с изолированными зависимостями;
- integration — service + repository + настоящая тестовая БД;
- e2e — HTTP API + service + repository + настоящая тестовая БД.

Интеграционные и e2e-тесты используют Testcontainers, поэтому для них должен работать Docker Desktop. Пример запуска внутри сервиса:

```powershell
uv sync --group dev
uv run pytest -q
```

Каждый сервис содержит собственный workflow `.github/workflows/ci-cd.yaml`: pull request запускает тесты, а push в `master` после успешной проверки публикует Docker-образ в GitHub Container Registry.

## Наблюдаемость

Все приложения пишут логи в stdout. Grafana Alloy получает логи контейнеров и отправляет их в Loki. Prometheus опрашивает `/metrics` у каждого backend-компонента, а Grafana автоматически получает оба источника данных.

Пример запроса логов в Grafana Explore:

```logql
{service="order-service"}
```

## Управление окружением

```powershell
docker compose ps
docker compose logs -f api-gateway
docker compose down
```

Удаление томов стирает локальные данные и должно выполняться осознанно:

```powershell
docker compose down --volumes
```
