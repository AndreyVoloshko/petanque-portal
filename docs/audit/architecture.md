# Architecture Audit

## Summary

The architecture is a classic monolithic Django application. The overall shape is valid for this type of portal. The issues are mixed responsibilities, business logic in wrong layers, and some configuration problems.

## System Architecture

```
Internet → Nginx (port 80/443) → Gunicorn (port 8000) → Django
                                                           ↓
                                                      PostgreSQL 17
                                                           ↓
                                                      S3 (static/media)
```

Deployment: Docker Compose with 5 services (web, nginx, db, adminer, certbot).

## Positive Aspects

- Domain concepts are recognizable and separated into model files (13 model files).
- Public views are split by feature area (15 view files).
- Templates are grouped by page/domain (63 templates in logical directories).
- Docker Compose describes the complete infrastructure.
- Django admin is configured for operational data management.
- Cron job for scheduled rating recalculation with proper env handling.
- URL patterns are named (enables `reverse()`).

## Main Architecture Smells

### Fat Models (Critical)

The largest business workflows live in model methods:

| Method | Lines | Location |
|--------|-------|----------|
| `Player.recalculate_ratings()` | ~85 | `models/player.py:159` |
| `Tournament.recalculate_power()` | ~35 | `models/tournament.py:103` |
| `Tournament.recalculate_ratings()` | ~32 | `models/tournament.py:209` |
| `Tournament.close_for_processing()` | ~25 | `models/tournament.py:178` |
| `Tournament.calculate_raw_team_rating_points()` | ~30 | `models/tournament.py:296` |
| `TeamTournamentMembership.recalculate_power()` | ~12 | `models/tournament.py:480` |

These are hard to test independently, hard to optimize, and easy to accidentally trigger.

### Views Mixing Too Many Concerns

The tournament detail view (`views/tournaments.py:30-87`) handles:
- GET rendering
- POST meta update (no auth check)
- POST final notes update (with auth)
- POST team deletion (with auth)
- POST team placement edits (with auth)
- Messages and redirects

This should be split into explicit action views.

### Template Filters As Data Access Layer

`app_filters.py` (757 lines) contains:
- 10+ filters that execute DB queries
- HTML building via string concatenation
- Ranking calculations
- Tournament/team lookups
- Display logic

Template filters should only format pre-loaded data.

### Context Processor Leaks Settings

`context_processors.py` passes the entire `settings` module to every template. This is both a security risk and an architecture smell — templates should receive only what they need.

### One Django App Contains Everything

The `federation` app (1327 lines of models, 757 lines of filters, ~800 lines of views) contains all domains. Acceptable for now, but internal modules would help:

```
federation/
├── services/        ← business logic
├── selectors/       ← query helpers
├── permissions.py   ← centralized auth checks
└── presenters/      ← view data preparation
```

### Legacy URL Patterns

All URLs use `re_path()` with regex patterns (Django 1.11 style). Modern Django uses `path()` with type converters. Not urgent but adds cognitive overhead.

### Error Handlers Are Broken

`federation/urls.py:82-90` defines `handler404` and `handler500` using Django 1.11's `context_instance` API, which was removed in Django 2.0. These handlers crash instead of rendering error pages.

## Recommended Architecture Direction

Keep the monolith. Do not rewrite into microservices or a separate React frontend. Introduce internal boundaries:

```text
federation/
├── services/
│   ├── tournament_registration.py
│   ├── tournament_processing.py
│   └── rating_calculation.py
├── selectors/
│   ├── players.py        ← annotated/prefetched querysets
│   ├── tournaments.py
│   └── statistics.py     ← aggregation queries
├── permissions.py
└── presenters/
    └── tournament_display.py  ← data prep currently in filters
```

This keeps deployment simple while making behavior testable and performance controllable.
