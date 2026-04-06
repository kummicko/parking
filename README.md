# Parking

A Django-based parking management application built with Python 3.12+, Docker, and Tailwind CSS.

## Tech Stack

- **Backend:** Django 6+
- **Package Manager:** [uv](https://github.com/astral-sh/uv)
- **Frontend:** Tailwind CSS
- **Server:** Gunicorn (production), Django dev server (development)
- **Containerization:** Docker & Docker Compose
- **Linting/Formatting:** Ruff

## Project Structure

```
parking/
├── src/
│   ├── accounts/       # User authentication & management
│   ├── home/           # Home page & core features
│   ├── parking/        # Django project settings & config
│   ├── static/         # Static assets (Tailwind input/output)
│   ├── templates/      # HTML templates
│   └── manage.py
├── docker-compose.yml          # Base compose config
├── docker-compose.override.yml # Dev overrides (hot-reload, debug)
├── docker-compose.prod.yml     # Production config
├── Dockerfile                  # Multi-stage build
├── pyproject.toml
└── docker-entrypoint.sh
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [uv](https://github.com/astral-sh/uv) (for local development)

## Getting Started

### Development

1. **Clone the repository:**

   ```bash
   git clone <repo-url>
   cd parking
   ```

2. **Create a `.env` file:**

   ```env
   APP_UID=1000
   APP_GID=1000
   SECRET_KEY=your-secret-key
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```

3. **Start the development server:**

   ```bash
   docker compose up
   ```

   The app will be available at `http://localhost:8000`. The dev server supports hot-reloading — edit code on your host and see changes instantly.

### Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

> **Note:** The production compose connects to an external `shared_web` network and exposes port 8000 internally (typically behind a reverse proxy).

## Available Commands

| Command | Description |
|---|---|
| `docker compose up` | Start dev server with hot-reload |
| `docker compose down` | Stop and remove containers |
| `docker compose exec parking python src/manage.py shell` | Open Django shell |
| `docker compose exec parking python src/manage.py createsuperuser` | Create admin user |

## Code Quality

This project uses **Ruff** for linting and formatting.

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .
```

Ruff rules enabled:
- Basic errors (`E`, `F`, `W`)
- Import sorting (`I`)
- Django-specific (`DJ`)
- Pyupgrade (`UP`)
- Bugbear (`B`)
- Security (`S`)

## Architecture

### Docker Multi-Stage Build

The `Dockerfile` uses two stages:

1. **Builder** — Installs dependencies via `uv`, downloads the Tailwind CSS CLI, and compiles minified CSS.
2. **Runtime** — Slim Python image with only the built artifacts and production dependencies.

### Entry Point

The `docker-entrypoint.sh` script runs on container start:

1. Validates the database directory is writable
2. Runs `makemigrations` and `migrate` automatically
3. Hands off to the main command (Gunicorn or runserver)

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `APP_UID` | `1000` | User ID for the container appuser |
| `APP_GID` | `1000` | Group ID for the container appgroup |
| `SECRET_KEY` | — | Django secret key (required) |
| `DEBUG` | `False` | Enable Django debug mode |
| `ALLOWED_HOSTS` | — | Comma-separated list of allowed hosts |

## Dependencies

### Production
- Django >= 6.0.1
- OpenAI >= 2.23.0
- python-dotenv >= 1.2.1
- Gunicorn >= 23.0.0
- WhiteNoise >= 6.11.0

### Development
- django-stubs >= 5.1.1
