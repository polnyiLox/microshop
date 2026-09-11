# ============================================================
# Builder
# ============================================================

FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Устанавливаем uv только на этапе сборки
COPY --from=ghcr.io/astral-sh/uv:0.10.0 /uv /uvx /bin/

# Сначала зависимости — Docker сможет кэшировать этот слой
COPY pyproject.toml uv.lock ./

# Создаём /app/.venv и устанавливаем production dependencies
RUN uv sync --frozen --no-dev

# Теперь копируем исходный код
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./


# ============================================================
# Runtime
# ============================================================

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Непривилегированный пользователь
RUN useradd \
    --create-home \
    --uid 10001 \
    --shell /usr/sbin/nologin \
    appuser

# Забираем только готовое приложение и venv
COPY --from=builder --chown=appuser:appuser /app /app

USER appuser

EXPOSE 8000

# Только API.
# Миграции запускаются отдельным service в Compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]