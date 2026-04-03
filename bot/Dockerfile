# syntax=docker/dockerfile:1
FROM python:3.14-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project metadata and workspace lock file for reproducible dependency install
COPY bot/pyproject.toml ./pyproject.toml
COPY uv.lock ./uv.lock

# Install dependencies (no source needed for layer cache)
RUN uv sync --frozen --no-dev

# Copy application source
COPY bot/bot.py bot/config.py ./
COPY bot/handlers/ ./handlers/
COPY bot/services/ ./services/

# Run the bot
CMD ["/app/.venv/bin/python3", "bot.py"]
