# MicroShop

Корневой Compose запускает весь MicroShop одной командой, сохраняя изоляцию микросервисов: у каждого сервиса собственная база и миграции, а RabbitMQ и Kafka используются как общая событийная инфраструктура.

## Быстрый запуск

Требуется Docker Desktop с Compose v2/v5. Файл `.env` необязателен: безопасные локальные значения уже имеют значения по умолчанию. Для своих паролей скопируйте `.env.example` в `.env`.

```powershell
docker compose up --build
```

После запуска доступны:

- frontend: <http://localhost:3000>;
- API Gateway: <http://localhost:8080>;
- Swagger Gateway: <http://localhost:8080/docs>;
- Grafana: <http://localhost:3001>;
- Prometheus: <http://localhost:9090>;
- Grafana Alloy: <http://localhost:12345>.

Для разработки с прямым доступом к Swagger каждого сервиса и инфраструктуре:

```powershell
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build
```

Сервисные API будут доступны на портах `8000`–`8005`, RabbitMQ UI — на `15672`, Kafka — на `9092`, MongoDB — на `27017`, PostgreSQL — на `54320`–`54324`.

## Управление

```powershell
docker compose ps
docker compose logs -f api-gateway
docker compose down
```

Удаление всех локальных данных выполняйте только когда они больше не нужны:

```powershell
docker compose down --volumes
```

Compose автоматически ждёт готовность баз и брокеров, выполняет Alembic-миграции и только затем запускает API. Внутренние сервисы общаются по DNS-именам Docker; наружу в обычном режиме открыты только frontend и Gateway.

## Логи и метрики catalog-service

Catalog-service пишет логи в stdout. Grafana Alloy читает логи Docker-контейнеров и отправляет их в Loki. Prometheus каждые 15 секунд получает HTTP-метрики с `catalog-service:8000/metrics`. Оба источника автоматически добавляются в Grafana.

После запуска откройте Grafana на <http://localhost:3001> и войдите с именем `admin`. Пароль задаётся переменной `GRAFANA_PASSWORD`; локальное значение по умолчанию — `microshop_dev_password`.

Логи можно посмотреть в разделе **Explore**, выбрав источник `Loki` и запрос:

```logql
{service="catalog-service"}
```

Для просмотра количества HTTP-запросов выберите источник `Prometheus` и выполните:

```promql
sum by (method, path, status) (rate(catalog_http_requests_total[5m]))
```

Для средней длительности запросов:

```promql
rate(catalog_http_request_duration_seconds_sum[5m])
/
rate(catalog_http_request_duration_seconds_count[5m])
```
