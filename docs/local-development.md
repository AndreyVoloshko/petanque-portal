# Local Development

This project is designed to run through Docker Compose. The main application is a Django service under `components/web-api/application/`.

> **Current workspace rule:** use the existing `petanque-portal` Compose project,
> containers, and volumes. The existing `petanque_portal_db` service and
> `petanque_db` volume contain production-derived data and are the local source
> of truth. Do not initialize, reset, reseed, replace, or remove that database
> unless explicitly asked.

See [the developer documentation entry point](README.md) and
[database schema reference](database-schema.md) before making high-risk changes.

## Prerequisites

- Docker
- Docker Compose v2
- Bash
- Python 3 (used by `deploy/local_run.sh` to read database settings from `APP_CREDENTIALS`)

## Existing Local Stack

Inspect the current stack with the explicit project name:

```bash
docker compose -p petanque-portal ps
```

Expected primary services:

- `petanque_portal_web_api`: app at `http://localhost:60102/`
- `petanque_portal_db`: production-derived local PostgreSQL source of truth
- `petanque_portal_adminer`: Adminer at `http://localhost:60103/`

Nginx may be stopped and is not the primary local entry point.

## Fresh Environment Setup Only

The following is for a genuinely new environment with no provided Compose stack
or database volume. Do not use it to replace the current workspace database.

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

## Start Or Rebuild The Existing App

For normal development, start/rebuild only the existing web service and its
dependencies:

```bash
docker compose -p petanque-portal up -d --build petanque_portal_web_api
```

When a rebuild is not needed:

```bash
docker compose -p petanque-portal restart petanque_portal_web_api
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

## Database Setup In A Fresh Environment Only

Do not run setup or fixture-loading commands against the provided
production-derived local database unless explicitly requested. In a genuinely
fresh environment, apply migrations with:

```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py migrate
```

Create an admin user:

```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py createsuperuser
```

The checked-in `db.json` is not the source of truth for this workspace. Loading
it can overwrite or conflict with existing data.

```bash
# Fresh/disposable environment only:
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
- Never use `docker compose down -v` in the provided workspace; it removes the
  source-of-truth database volume.
