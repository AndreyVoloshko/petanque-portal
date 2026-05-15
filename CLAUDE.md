# Petanque Portal

Web portal for the Ukrainian Petanque Federation (`portal.petanque.org.ua`). Django 5 + PostgreSQL 17, server-rendered templates, single-server Docker Compose deployment.

## Quick Commands

Start local stack:
```bash
./deploy/local_run.sh
```

All `manage.py` commands run inside the container:
```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py <command>
```

Common ones:
- `migrate` — apply pending migrations
- `makemigrations` — generate migration after a model change
- `createsuperuser` — create admin account
- `check` — run Django system checks
- `test` — run test suite
- `recalculate_ratings` — recalculate all player ratings manually
- `shell` — interactive Django shell

## Project Layout

```
components/web-api/application/   ← Django root (almost all coding happens here)
  api/settings.py                  ← Settings (reads APP_CREDENTIALS from env)
  api/urls.py                      ← Top-level routing
  federation/                      ← Main app
    models/                        ← Player, Club, Tournament, Season, Team, etc.
    views/                         ← Function-based views
    templates/                     ← Django HTML templates (Bootstrap 5)
    forms/                         ← Django forms
    admin.py                       ← Admin registrations
    admin_actions/                 ← Bulk admin actions
    management/commands/           ← Custom manage.py commands
    migrations/                    ← Migration history (72 files)
    templatetags/                  ← Custom template filters
    helpers/                       ← Shared utilities
    storage.py                     ← S3 storage backends
    config/                        ← Rating constants
docker-compose.yml
deploy/                            ← local_run.sh, remote_run.sh, remote_destroy.sh
docs/                              ← project-overview.md, local-development.md
```

## Architecture Conventions

- **No frontend framework.** All UI is server-rendered Django templates + Bootstrap 5 + vanilla JS. New features = view + template + form.
- **Function-based views** throughout. Keep new views consistent with the existing style.
- **Configuration via `APP_CREDENTIALS`** — a single JSON env var in `.env`. Never hardcode credentials or secrets.
- **S3 for static/media in production.** Falls back to local filesystem when S3 credentials are absent (safe for local dev).
- **No CI/CD.** Deployment is manual via `./deploy/remote_run.sh` on the server.

## Local Services

| Service | URL | Purpose |
|---|---|---|
| Django app | http://localhost:60102/ | Main application |
| Django admin | http://localhost:60102/admin/ | Admin interface |
| Adminer | http://localhost:60103/ | Database UI |
| Nginx | http://localhost:80/ | Reverse proxy (optional locally) |

## Key Constraints

- **Migrations:** always run `makemigrations` + `migrate` after model changes. Never edit existing migration files.
- **Ratings logic is complex.** `Player`, `Tournament` models and `recalculate_ratings` command contain the core business logic — change carefully and test manually.
- **No meaningful test coverage.** `federation/tests.py` is a placeholder. Write tests when touching rating/tournament processing.
- **Ukrainian locale.** User-visible strings should use `_()` / `gettext`. Translations live in `locale/uk/LC_MESSAGES/django.po`.
- **`db.json`** is a data fixture for local seeding — treat as read-only unless intentionally refreshing it.
- **`CORS_ORIGIN_ALLOW_ALL = True`** is set globally (GET only). Do not add new cross-origin endpoints without reviewing this.
