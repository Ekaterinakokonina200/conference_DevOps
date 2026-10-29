# Образ приложения Conference Management System (ЛР №4).
#
# Воспроизводимость сборки:
#   - базовый образ закреплён по версии И по дайджесту sha256 (make pin-images),
#     поэтому через месяц собирается тот же самый Python, а не «какой-то 3.12»;
#   - зависимости ставятся строго по requirements.txt (все версии через ==)
#     с --no-deps, а pip check проверяет, что набор полный и согласованный;
#   - в контекст сборки попадают только нужные файлы (.dockerignore — белый список).
#
# Безопасность:
#   - процесс работает от пользователя app (UID 10001), а не от root;
#   - файлы приложения принадлежат root и доступны пользователю app только
#     на чтение;
#   - секретов в образе нет: .env, .env.* в контекст сборки не попадают,
#     настройки передаются переменными окружения при запуске.

# ---------- этап 1: сборка зависимостей ----------
FROM python:3.12.15-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70 AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-deps -r requirements.txt \
    && /opt/venv/bin/pip check

# ---------- этап 2: итоговый образ ----------
FROM python:3.12.15-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70 AS runtime

ARG APP_VERSION=0.5.0

LABEL org.opencontainers.image.title="conference-app" \
      org.opencontainers.image.description="Conference Management System (FastAPI)" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.source="https://github.com/Ekaterinakokonina200/conference_DevOps"

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION="${APP_VERSION}"

# Непривилегированный системный пользователь без домашнего каталога и оболочки
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app \
       --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin app

# Обновления безопасности Debian, вышедшие после сборки базового образа
RUN apt-get update \
    && apt-get install -y --no-install-recommends --only-upgrade libssl3 openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

USER 10001:10001

EXPOSE 8000

# docker stop отправляет SIGTERM; uvicorn по нему перестаёт принимать
# новые соединения, ждёт завершения текущих (не дольше 10 с) и выходит с кодом 0.
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

# Форма exec (JSON-массив): uvicorn — процесс №1 и сам получает сигнал.
# В форме shell сигнал получил бы /bin/sh, а приложение было бы убито через 10 с.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--timeout-graceful-shutdown", "10", "--no-server-header"]
