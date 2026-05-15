# Local Development

This project is designed to run through Docker Compose. The main application is a Django service under `components/web-api/application/`.

## Prerequisites

- Docker
- Docker Compose v2

## First-Time Setup

Create a local environment file:

```bash
cp .env.sample .env
```

The sample environment is configured for the Compose PostgreSQL service:

- database host: `petanque_portal_db`
- database name: `petanque_portal`
- database user: `postgres`
- database password: `petanque_portal_db_password`
- database port: `5432`

The sample leaves S3 credentials empty. When S3 credentials are absent, the app falls back to local static/media URLs.

## Start The App

Recommended local command:

```bash
docker compose -p petanque-portal up --build petanque_portal_db petanque_portal_web_api petanque_portal_adminer
```

Then open:

- Django app: `http://localhost:60102/`
- Adminer: `http://localhost:60103/`
- Django admin: `http://localhost:60102/admin/`

The Nginx service maps ports `80` and `443`. Start it only if you specifically want to test Nginx behavior:

```bash
docker compose -p petanque-portal up --build
```

## Database Setup

After containers are running, apply migrations:

```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py migrate
```

Create an admin user:

```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py createsuperuser
```

Optional: load the checked-in JSON data if it is intended for local use:

```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py loaddata db.json
```

## Useful Commands

Run Django checks:

```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py check
```

Run tests:

```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py test
```

Open a Django shell:

```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py shell
```

Run the rating recalculation command manually:

```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py recalculate_ratings
```

Stop containers:

```bash
docker compose -p petanque-portal down
```

Stop containers and remove volumes:

```bash
docker compose -p petanque-portal down -v
```

## Local Runtime Notes

- The service container runs Gunicorn on port `8000`; Compose exposes it on host port `60102`.
- Supervisor starts both the web service and cron.
- The weekly cron job runs `python manage.py recalculate_ratings` from `/application`.
- Local media files are stored in the `petanque_uploaded_files` Docker volume.
- Production S3 storage is used only when all S3 credentials are present in `APP_CREDENTIALS`.
