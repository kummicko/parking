# --- Stage 6: Build ---
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_SYSTEM_PYTHON=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local

WORKDIR /app

COPY pyproject.toml uv.lock ./

# Sync base dependencies + prod group only (excludes dev dependencies)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group prod

# Download standalone Tailwind CLI and compile CSS
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 \
    && chmod +x tailwindcss-linux-x64 \
    && mv tailwindcss-linux-x64 /usr/local/bin/tailwindcss \
    && apt-get purge -y curl && rm -rf /var/lib/apt/lists/*

COPY src/ /app/src/

# Build Tailwind CSS (same paths as tw-dev alias, but minified)
RUN tailwindcss -i src/static/tw/input.css -o src/static/css/ui.css --minify

# --- Stage 2: Runtime ---
FROM python:3.13-slim-trixie
WORKDIR /app

# Accept IDs from docker-compose
ARG UID=1000
ARG GID=1000

# Create group and user using the dynamic ARGs
RUN groupadd -g "${GID}" appgroup || true && \
    useradd -l -u "${UID}" -g "${GID}" -m -s /bin/bash appuser || true

# Copy the entire /usr/local directory where uv installed everything
COPY --from=builder /usr/local /usr/local

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY --chown=appuser:appgroup src/ /app/src/

# Override with the minified compiled CSS from builder
COPY --chown=appuser:appgroup --from=builder /app/src/static/css/ui.css /app/src/static/css/ui.css

COPY --chown=appuser:appgroup pyproject.toml README.md docker-entrypoint.sh /app/

RUN mkdir -p /app/src/db /app/staticfiles && chown -R appuser:appgroup /app/src/db /app/staticfiles
RUN chmod +x /app/docker-entrypoint.sh

USER appuser

RUN SECRET_KEY=build-secret DEBUG=False ALLOWED_HOSTS=localhost \
    python src/manage.py collectstatic --noinput --clear

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--chdir", "src", "parking.wsgi:application"]
