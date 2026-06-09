# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements/prod.txt

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8001

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --gid 1001 tabi && \
    useradd --uid 1001 --gid tabi --shell /bin/bash --create-home tabi

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

RUN chown -R tabi:tabi /app

USER tabi

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
