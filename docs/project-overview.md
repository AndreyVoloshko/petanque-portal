# Petanque Portal Project Overview

This repository contains the Django application behind `https://portal.petanque.org.ua/`, a portal for the Ukrainian petanque federation. It manages players, clubs, tournaments, ratings, teams, documents, national teams, departments, seasons, arbiters, coaches, and related public pages.

## High-Level Structure

```text
.
├── docker-compose.yml
├── .env.sample
├── deploy/
│   ├── local_run.sh
│   ├── remote_run.sh
│   ├── remote_destroy.sh
│   └── init-letsencrypt.sh
├── components/
│   └── web-api/
│       ├── Dockerfile.service
│       ├── Dockerfile.nginx
│       ├── conf/
│       │   ├── supervisor-app.conf
│       │   ├── web-service-server.conf
│       │   └── crontab.txt
│       └── application/
│           ├── manage.py
│           ├── requirements.txt
│           ├── gunicorn_start
│           ├── db.json
│           ├── api/
│           ├── federation/
│           ├── static/
│           └── locale/
└── docs/
    └── project-overview.md
```

The actual application code is in `components/web-api/application/`. The root mostly contains Docker orchestration and deployment helpers.

## Technology Stack

- Backend framework: Django `5.1.6`
- Language/runtime: Python `3.11` in the service container
- Database: PostgreSQL `17`, configured through Docker Compose
- Web server: Gunicorn behind Nginx
- Process manager: Supervisor
- Scheduled tasks: cron inside the service container
- Admin/database helper: Adminer exposed by Docker Compose
- Static/media storage: `django-storages` with S3/Boto3
- Forms/UI helpers: `django-crispy-forms`, `crispy-bootstrap5`, Bootstrap CSS
- Country fields: `django-countries`
- CAPTCHA: `django-simple-captcha`
- Profiling/debug tooling: `django-silk`, `django-extensions`
- CORS: `django-cors-headers`
- Frontend style: server-rendered Django templates plus static CSS/JS, not a separate React/Vue/etc app
- JavaScript libraries in repo: DataTables, FullCalendar, Moment, custom `scripts.js`

There is no `package.json`, Node build pipeline, or separate frontend application in this clone.

## Docker And Runtime Services

`docker-compose.yml` defines these services:

- `petanque_portal_web_api`: builds `components/web-api/Dockerfile.service`, runs the Django app on container port `8000`, exposed locally as `60102`.
- `petanque_portal_nginx`: builds `components/web-api/Dockerfile.nginx`, proxies traffic to the Django container, exposes HTTP `80` and HTTPS `443`.
- `petanque_portal_db`: PostgreSQL 17 database with persistent volume `petanque_db`.
- `petanque_portal_adminer`: Adminer UI exposed locally as `60103`.
- `certbot`: renewal loop for Let's Encrypt certificates.

Persistent Docker volumes:

- `petanque_db`: PostgreSQL data.
- `petanque_uploaded_files`: mounted to `/application/media/images/` for uploaded images.

Deployment scripts are in `deploy/`:

- `local_run.sh`: loads `.env` and runs `docker compose -p "petanque-portal" up --build`.
- `remote_run.sh`: same, but detached with `-d`.
- `remote_destroy.sh`: stops the compose project.
- `init-letsencrypt.sh`: obtains certificates for `portal.petanque.org.ua`.

## Django Project Layout

The Django project root is:

```text
components/web-api/application/
```

Important files:

- `manage.py`: Django management entry point.
- `api/settings.py`: global Django settings.
- `api/urls.py`: top-level URL configuration. It mounts `/admin/` and includes all `federation.urls`.
- `api/wsgi.py`: WSGI entry point used by Gunicorn.
- `requirements.txt`: Python dependencies.
- `gunicorn_start`: app launch script used by Supervisor.
- `db.json`: checked-in data fixture or dump-like JSON file.

The main Django app is:

```text
components/web-api/application/federation/
```

Key subdirectories:

- `models/`: domain data models.
- `views/`: function-based views for public pages and JSON endpoints.
- `templates/`: Django templates organized by feature.
- `forms/`: Django forms for profile/player/team registration.
- `admin_actions/`: admin actions for players, tournaments, and seasons.
- `management/commands/`: custom Django management commands.
- `migrations/`: database migration history.
- `templatetags/`: custom template filters.
- `helpers/`: small shared helpers.
- `config/`: rating-related constants.

## Configuration

The app expects most environment configuration through a single JSON environment variable called `APP_CREDENTIALS`. A sample is provided in `.env.sample`.

Main configured values:

- `debug`
- `domains`
- `csrf_origins`
- `language`
- `country`
- `db_host`, `db_name`, `db_user`, `db_pass`, `db_port`
- `s3_key`, `s3_secret`, `s3_bucket`, `s3_region`, `s3_backups_folder`
- `recaptcha_public_key`, `recaptcha_private_key`

`api/settings.py` uses PostgreSQL as the database engine and S3 for static/media storage:

- `STATICFILES_STORAGE = 'federation.storage.StaticStorage'`
- `DEFAULT_FILE_STORAGE = 'federation.storage.MediaStorage'`
- `DBBACKUP_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'`

The project language/country defaults are configured from credentials. The locale folder contains Ukrainian translations:

```text
components/web-api/application/locale/uk/LC_MESSAGES/django.po
```

## Main Domain Models

Models live in `components/web-api/application/federation/models/`.

Important model files:

- `player.py`: `Player`; extends Django `User` through a one-to-one relation and stores profile, license, club, country, gender, rating, arbiter, coach, and sport-title information.
- `club.py`: `Club`; club data and admin configuration.
- `city.py`: `City`; city lookup model.
- `team.py`: `Team`, `PlayerTeamMembership`; teams are many-to-many with players through a membership table and have captain support.
- `tournament.py`: `Tournament`, `TeamTournamentMembership`, `ArbiterTournamentMembership`; tournament metadata, registration, rating/power calculations, teams, arbiters, protocols, and processing state.
- `season.py`: `Season`; season/rating period data and admin configuration.
- `record.py`: `Record`; federation records.
- `document.py`: `DocumentCategory`, `Document`; uploaded documents grouped by categories.
- `national_teams.py`: `National_team`, `PlayerNational_teamMembership`; national team rosters.
- `department.py`: `Department`, `PlayerDepartmentMembership`; regional/department membership.

The most complex business logic is in `Player`, `Team`, and `Tournament`, especially rating calculation and tournament processing.

## URLs And Views

Top-level routing:

- `components/web-api/application/api/urls.py`
- `components/web-api/application/federation/urls.py`

Main public routes:

- `/`: main page with top players and upcoming tournaments.
- `/login/`, `/logout/`, `/profile/`: authentication/profile pages.
- `/clubs/`, `/club/<id>`: clubs list and club detail.
- `/players/`, `/player/<id>`: players list and player detail.
- `/tournaments/`, `/tournament/<id>`: tournaments list and detail.
- `/calendar/`: tournament calendar page.
- `/register/team/<tournament_id>`: team registration for a tournament.
- `/register/player/`: player registration.
- `/national_teams/`: national teams.
- `/arbiters/`, `/coaches/`: filtered player pages for arbiters/coaches.
- `/records/`: federation records.
- `/sport_titles/`: sport title page.
- `/documents/`: documents page.
- `/departments/`: departments page.
- `/season/`, `/season/<year>`: season pages.
- `/statistics/`, `/statistics/<year>`: statistics pages.
- `/admin/`: Django admin.

JSON/API-like routes:

- `/api/tournaments/list/`: calendar event data for tournaments.
- `/api/players_clubs_and_tournaments/list/`: search suggestions across players, clubs, and tournaments.
- `/api/players_list/list/`: player search endpoint, likely used by select widgets.

The view layer is mostly function-based and maps directly to template files.

## Templates And Static Assets

Templates are in:

```text
components/web-api/application/federation/templates/
```

Template groups:

- `common/`: base layout, header, footer, menu, reusable page wrappers.
- `main_page/`: partials for main-page lists.
- `players/`: player pages, cards, tables, rating/stat panels.
- `clubs/`: club list/detail/card/table templates.
- `tournaments/`: tournament pages, calendar, teams, protocol, summary, delegations.
- `register/`: team and player registration.
- `national_teams/`, `seasons/`, `records/`, `documents/`, `departments/`, `statistics/`: feature pages.
- `admin/`: custom admin action confirmation template.

Static files are in:

```text
components/web-api/application/static/
```

Important static files:

- `style.css`, `style-v2.css`: project styling.
- `scripts.js`: custom JavaScript.
- `bootstrap-theme.css`: Bootstrap theme.
- `jquery.dataTables.js`, `dataTables.bootstrap.js`, `dataTables.bootstrap.css`: table UI.
- `calendar_full_calendar*.js/css`, `calendar_moment.min.js`: calendar UI.
- images/icons such as `default.png`, `404.jpg`, `countries.png`, `favicon.ico`.

## Admin Area

Admin registration is centralized in:

```text
components/web-api/application/federation/admin.py
```

Registered models include:

- `City`
- `Club`
- `Player`
- `Team`
- `Tournament`
- `National_team`
- `Record`
- `DocumentCategory`
- `Document`
- `Season`
- `Department`

Several model files also define their own `ModelAdmin` classes and inline classes. Tournament and player admin actions are imported from `federation/admin_actions/`.

## Scheduled And Management Tasks

Custom command:

```text
components/web-api/application/federation/management/commands/recalculate_ratings.py
```

It recalculates ratings for all currently licensed players.

The cron config is:

```text
components/web-api/conf/crontab.txt
```

It is intended to run rating recalculation weekly. One thing to verify before production use: the cron file uses `cd /app`, while the Dockerfile copies the project to `/application`.

## Storage

Storage classes are in:

```text
components/web-api/application/federation/storage.py
```

`StaticStorage`, `MediaStorage`, and `AvatarsStorage` extend `S3Boto3Storage`. Uploaded media filenames are replaced with an MD5 hash of the current timestamp plus the original file extension.

Nginx also serves local `/static/` and `/media/images/` aliases from the container filesystem. At the Django settings level, static and media URLs are configured for S3.

## Tests

There is currently only the default placeholder:

```text
components/web-api/application/federation/tests.py
```

No meaningful automated tests are present in this clone.

## Notes For Future Development

- The project is a classic server-rendered Django app, so new UI features should usually be implemented with Django views, templates, forms, and static CSS/JS unless a frontend migration is planned.
- Business rules for ratings and tournament processing are embedded in model methods and admin actions. Changes there should be made carefully and backed by tests.
- The codebase uses Django 5.1.6, but some comments and patterns are inherited from an older Django 1.11 project.
- The checked-in settings include a hardcoded `SECRET_KEY`; production should rely on environment-managed secrets.
- `CORS_ORIGIN_ALLOW_ALL = True` and `CORS_ALLOW_METHODS = ['GET']` are globally configured. Verify this matches the real security requirements.
- `DEBUG`, `ALLOWED_HOSTS`, database, S3, and CAPTCHA settings all depend on valid `APP_CREDENTIALS`.
- There is no local `AGENTS.md` or `RTK.md` file in this clone at the time this document was created.
