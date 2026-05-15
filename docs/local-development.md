# Local Development

This project is designed to run through Docker Compose. The main application is a Django service under `components/web-api/application/`.

## Prerequisites

- Docker
- Docker Compose v2
- Bash
- Python 3 (used by `deploy/local_run.sh` to read database settings from `APP_CREDENTIALS`)

## First-Time Setup

Create a local environment file:

```bash
cp .env.sample .env
```

Edit `APP_CREDENTIALS` in `.env` so the app and Postgres container use the same database settings. For local Compose, use the Postgres service hostname:

- `db_host`: `petanque_portal_db`
- `db_name`: `petanque_portal`
- `db_user`: `postgres`
- `db_pass`: `petanque_portal_db_password`
- `db_port`: `5432`

`deploy/local_run.sh` exports `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` from those `db_*` fields before starting Compose.

The sample leaves S3 credentials empty. When S3 credentials are absent, the app falls back to local static/media URLs.

## Deploy Scripts

Scripts in `deploy/` source `.env` and run Compose with project name `petanque-portal`.

| Script | Purpose |
| --- | --- |
| `deploy/local_run.sh` | Local development: export Postgres credentials from `APP_CREDENTIALS`, then `docker compose up --build` (foreground, all services). |
| `deploy/remote_run.sh` | Remote/server: `docker compose up --build -d` (detached). |
| `deploy/remote_destroy.sh` | Remote/server: `docker compose down`. |
| `deploy/init-letsencrypt.sh` | Request initial Let's Encrypt certificates via the `certbot` service (production; requires Nginx and `data/certbot/` volumes). |

Run from the repository root:

```bash
./deploy/local_run.sh
```

## Start The App

Recommended local command:

```bash
./deploy/local_run.sh
```

This starts the full stack (web API, Postgres, Adminer, Nginx, Certbot). To run only the app, database, and Adminer without Nginx:

```bash
docker compose -p petanque-portal up --build petanque_portal_db petanque_portal_web_api petanque_portal_adminer
```

When using the manual command, export Postgres variables yourself (or use the same values as in `APP_CREDENTIALS`):

```bash
export POSTGRES_DB=petanque_portal
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=petanque_portal_db_password
```

Then open:

- Django app: `http://localhost:60102/`
- Adminer: `http://localhost:60103/`
- Django admin: `http://localhost:60102/admin/`

The Nginx service maps ports `80` and `443`. It is included when you use `./deploy/local_run.sh`. Start it only if you specifically want to test Nginx behavior:

```bash
docker compose -p petanque-portal up --build petanque_portal_nginx
```

For initial TLS certificates on a server with Nginx running, use:

```bash
./deploy/init-letsencrypt.sh
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

On a remote host, prefer the deploy scripts:

```bash
./deploy/remote_destroy.sh
```

## Local Runtime Notes

- The service container runs Gunicorn on port `8000`; Compose exposes it on host port `60102`.
- Supervisor starts both the web service and cron.
- The weekly cron job runs `python manage.py recalculate_ratings` from `/application`.
- Local media files are stored in the `petanque_uploaded_files` Docker volume.
- Production S3 storage is used only when all S3 credentials are present in `APP_CREDENTIALS`.
