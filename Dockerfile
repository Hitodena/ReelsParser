FROM python:3.12-slim AS base

# Install system dependencies and cleanup
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Install UV package manager
RUN pip install --no-cache-dir uv

# Create non-root user
RUN useradd -m -s /bin/bash docker_user

# Set working directory and fix permissions
WORKDIR /app
RUN chown -R docker_user:docker_user /app

# Switch to non-root user
USER docker_user

# Copy dependency files
COPY --chown=docker_user:docker_user pyproject.toml uv.lock ./

# Install dependencies
ENV UV_HTTP_TIMEOUT=300
RUN uv sync

FROM base AS api

# Switch to root to install
USER root

# Install playwright deps
RUN uv run playwright install-deps chromium

# Switch back to user
USER docker_user

# Install playwright browser
RUN uv run playwright install chromium

# Copy application code
COPY --chown=docker_user:docker_user app ./app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "-m", "app.main"]

FROM base AS bot

# Copy application code
COPY --chown=docker_user:docker_user app ./app
COPY --chown=docker_user:docker_user bot ./bot

# Run the bot
CMD ["uv", "run", "-m", "bot.main"]
