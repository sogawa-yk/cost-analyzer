# Build stage
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.13-slim

RUN groupadd -r app && useradd -r -g app app

WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY --from=builder /app/src src

ENV PATH="/app/.venv/bin:$PATH"
USER app

ENTRYPOINT ["python", "-m", "cost_analyzer"]
