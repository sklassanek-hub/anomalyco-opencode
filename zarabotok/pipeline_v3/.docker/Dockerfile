# Минимальный контейнер для выполнения задач (executor.py) — §11.3 fusion-response
# Read-only системный образ + отдельный non-root пользователь
FROM python:3.12-slim

# Не запускать от root
RUN useradd -m -u 1001 executor && \
    mkdir -p /workspace && chown -R executor:executor /workspace

# Системный образ минимальный, без лишних пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Read-only образ по умолчанию: только /workspace — запись разрешена
# (в docker-compose или docker run монтируем workspace как volume, 
#  а rootfs остаётся read-only через docker run --read-only или в compose)
USER executor

# Ограничение ресурсов задаётся вне контейнера (docker run --memory --cpus)
ENTRYPOINT ["python3"]
