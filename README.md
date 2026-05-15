# Petanque Portal

Web portal for the Ukrainian Petanque Federation — [portal.petanque.org.ua](https://portal.petanque.org.ua).

Manages players, clubs, tournaments, ratings, teams, national teams, arbiters, coaches, documents, and seasons.

**Stack:** Django 5 · PostgreSQL 17 · Nginx · Docker Compose · S3

## Quick Start

```bash
cp .env.sample .env
# Fill in APP_CREDENTIALS in .env (db credentials, S3, recaptcha)
./deploy/local_run.sh
```

Then apply migrations and create a superuser:

```bash
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py migrate
docker compose -p petanque-portal exec petanque_portal_web_api python manage.py createsuperuser
```

Open:

* App: [http://localhost:60102/](http://localhost:60102/)
* Admin: [http://localhost:60102/admin/](http://localhost:60102/admin/)
* DB Adminer: [http://localhost:60103/](http://localhost:60103/)

## Docs

* [Local development](docs/local-development.md)
* [Project overview](docs/project-overview.md)
* [Audit](docs/audit/README.md)

