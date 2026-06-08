# syntax=docker/dockerfile:1.7-labs
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /repo
COPY packages/athean-core /repo/packages/athean-core
COPY apps/api /repo/apps/api

WORKDIR /repo/apps/api
RUN uv sync --frozen --no-dev || uv sync --no-dev

ENV PYTHONPATH=/repo/packages/athean-core/src:/repo/apps/api/src

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "athean_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
