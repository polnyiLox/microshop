# API Gateway

Единая внешняя HTTP- и WebSocket-точка входа MicroShop. Gateway проверяет JWT,
применяет role-based access, формирует доверенные identity headers и проксирует
запросы во внутренние сервисы.

## Ответственность

- проверка access-токена публичным RS256-ключом;
- маршрутизация запросов по сервисам;
- удаление присланных клиентом `X-User-ID` и `X-User-Role`;
- передача проверенных `sub` и `role` во внутренние сервисы;
- ограничения публичных inventory, payment и order-status операций;
- WebSocket proxy для уведомлений;
- единая CORS-политика для frontend.

CORS находится только в Gateway. Внутренние микросервисы не обслуживают
браузерный cross-origin traffic напрямую.

## Архитектура

```text
app/
├── api/             # proxy routers, dependencies и error handlers
├── clients/         # HTTP forwarding
├── core/            # Settings, health check, logging и metrics
├── security/        # проверка JWT
├── websocket/       # notification WebSocket proxy
└── main.py          # FastAPI и CORS
```

## Маршрутизация

| Путь | Сервис | Доступ |
|---|---|---|
| `/v1/auth/...` | auth-service | публичные и защищённые auth endpoints |
| `GET /v1/products/...` | catalog-service | публично |
| запись `/v1/products/...` | catalog-service | `seller` |
| `/v1/orders/...` | order-service | свой пользователь |
| `/v1/payments/...` | payment-service | свой пользователь |
| `/v1/notifications/...` | notification-service | свой пользователь |
| `/v1/analytics/...` | analytics-service | `admin` |

Произвольное изменение статуса заказа, создание платежа и inventory-команды
через Gateway не публикуются. Эти операции выполняются внутренним бизнес-процессом.

Proxy routes скрыты из Swagger, поскольку Gateway не дублирует DTO всех
сервисов. Полные схемы доступны в Swagger соответствующего микросервиса.

## WebSocket уведомлений

Публичный URL не содержит `user_id` или токен:

```javascript
const socket = new WebSocket(
  "ws://localhost:8080/v1/notifications/ws",
  ["bearer", accessToken],
);
```

Gateway извлекает пользователя из JWT и сам формирует внутренний WebSocket URL.

## JWT-ключ

Gateway содержит только `certs/jwt-public.pem`. После ротации ключей auth-service
публичный ключ необходимо синхронно заменить и перезапустить Gateway.

## Запуск всего проекта

Из корня репозитория:

```powershell
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build
```

После запуска:

- Gateway: <http://localhost:8080>;
- health check: <http://localhost:8080/health>;
- Swagger: <http://localhost:8080/docs>;
- frontend: <http://localhost:3000>.

## Локальная разработка

```powershell
Copy-Item .env.example .env
uv sync --frozen
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Адреса из `APP_CONFIG__SERVICES__...` должны указывать на запущенные backend
сервисы. CORS origins задаются только в настройках Gateway.

## Тесты

```powershell
uv run pytest -q
```

Unit-тесты проверяют JWT, role-based access, доверенные headers, HTTP proxy и
WebSocket URL. E2e-тест проходит через настоящий Gateway до тестового upstream.

## CI/CD

Workflow `.github/workflows/ci-cd.yaml` запускает тесты для pull request и push
в `master`. После успешного push публикуются образы
`ghcr.io/<github-owner>/api-gateway:latest` и `:sha-<commit>`.
