# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# uv provides fast, reproducible installs from the committed lockfile.
COPY --from=ghcr.io/astral-sh/uv:0.12.4 /uv /bin/uv

WORKDIR /code

# Install dependencies first (cached) using only the lock + manifest.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
RUN uv sync --frozen --no-dev

ENV PATH="/code/.venv/bin:$PATH"
EXPOSE 8000

# Railway: run migrations as a pre-deploy step, then start the app.
# The app binds to localhost by default; Railway reaches it over the private network.
CMD ["sh", "-c", "uvicorn app.services:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'"]
