# Auth Service

Сервис аутентификации и авторизации MicroShop. Хранит пользователей и
refresh-токены, выдаёт подписанные JWT, управляет ролями и балансом пользователя.

## Ответственность

- регистрация по email и российскому номеру телефона;
- вход по email или номеру телефона;
- хеширование паролей с Argon2;
- выпуск access-токенов с подписью RS256;
- одноразовая ротация refresh-токенов;
- завершение одной или всех пользовательских сессий;
- назначение ролей `user`, `seller` и `admin`;
- пополнение и снятие средств пользователем;
- идемпотентные внутренние операции списания и возврата средств.

Приватный JWT-ключ хранится только в auth-service. API Gateway использует
соответствующий публичный ключ и не подключается к базе пользователей.

## Архитектура

```text
app/
├── api/             # endpoints и зависимости аутентификации
├── cache/           # контракт кэша и Redis-клиент
├── db/models/       # User и RefreshToken
├── repositories/    # запросы SQLAlchemy
├── schemas/         # регистрация, вход, токены и роли
├── security/        # JWT, пароли и refresh-токены
├── services/        # бизнес-логика сессий и баланса
└── main.py          # FastAPI-приложение
```

Внутренний сервис не содержит CORS middleware. Политика доступа браузера
настраивается в API Gateway.

## HTTP API

Основные маршруты аутентификации имеют префикс `/v1/auth`:

- `POST /register`;
- `POST /login/email`;
- `POST /login/phone_number`;
- `POST /refresh`;
- `POST /logout`;
- `POST /logout/all`;
- `GET /me`;
- `PATCH /users/{user_id}/role` — только для администратора;
- `GET /balance`, `POST /balance/deposit`, `POST /balance/withdraw`;
- `POST /v1/internal/users/{user_id}/balance/debit` и `/credit` — внутренние
  операции, защищённые `X-Internal-Token`;
- `GET /health` — состояние приложения (без префикса `/v1`).

Refresh-токен передаётся в `HttpOnly` cookie. Endpoint `/refresh` отзывает
использованный токен и записывает новый.

Swagger при development-запуске: <http://localhost:8000/docs>.

## Запуск всего проекта

Из корня репозитория:

```powershell
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build
```

Перед API автоматически запускается контейнер `auth-migrate`, выполняющий
`alembic upgrade head`.

## Локальная разработка

Сначала создайте RSA-ключи, которые не хранятся в Git:

```powershell
New-Item -ItemType Directory -Force certs | Out-Null
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out certs/jwt-private.pem
openssl pkey -in certs/jwt-private.pem -pubout -out certs/jwt-public.pem
```

Затем настройте окружение и запустите сервис:

```powershell
Copy-Item .env.example .env
uv sync --frozen
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Для локального запуска измените адрес PostgreSQL в `.env` с Docker DNS-имени
на `localhost`. Приватный ключ нельзя добавлять в Git или передавать другим
сервисам.

## Тесты

```powershell
uv run pytest -q
```

Интеграционные и e2e-тесты PostgreSQL используют Testcontainers.

## CI/CD

Workflow `.github/workflows/ci-cd.yaml` запускает тесты для pull request и push
в `master`. После успешного push публикуются образы
`ghcr.io/<github-owner>/auth-service:latest` и `:sha-<commit>`.
