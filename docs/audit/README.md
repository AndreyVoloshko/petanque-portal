# Application Audit

This audit reviews the `portal.petanque.org.ua` repository as it exists locally. The app is a Dockerized, server-rendered Django portal with the main code under `components/web-api/application/`.

## Overall Assessment

The project has a coherent Django shape and reflects a working production portal, but it is a legacy-style Django application that has been upgraded to newer dependencies without a matching modernization pass. The main risks are security gaps around state-changing views, exposed secrets in multiple layers, weak runtime configuration discipline, no meaningful tests, 178 instances of `|safe` template rendering, repeated inline frontend code, and high business-logic concentration in models/templates/filters.

Approximate quality rating: **3.5/10 to 4.5/10** (revised down from initial assessment after deeper code inspection).

This does not mean the app is unsalvageable. It means the best path is stabilization and incremental modernization, not a rewrite.

## Audit Files

- [Security](security.md) — Critical vulnerabilities and hardening gaps
- [Architecture](architecture.md) — System structure and separation of concerns
- [Backend And Django Usage](backend-django.md) — Framework usage patterns and anti-patterns
- [Frontend And UI](frontend-ui.md) — Template/JS/CSS state
- [Performance](performance.md) — Query patterns and rendering bottlenecks
- [Found Bugs And Correctness Risks](found-bugs.md) — Concrete bugs from static inspection
- [Legacy And Modernization](legacy.md) — Technical debt and upgrade path
- [Dependencies And Upgrades](dependencies-upgrades.md) — Package management state
- [Deployment And Runtime](deployment-runtime.md) — Docker/infrastructure concerns
- [Testing And Quality Gates](testing-quality.md) — Testing and CI gaps
- [Data Model And Domain Logic](data-model-domain.md) — Domain modeling and business logic

## Highest-Impact Findings (Prioritized)

### Critical Security

1. **Tournament detail view is `@csrf_exempt` with unauthenticated mutation** — `meta` field is updated before any auth check (line 36-38 of `views/tournaments.py`).
2. **Django `SECRET_KEY` hardcoded in source** — `api/settings.py:33`.
3. **Settings context processor leaks all Django settings to templates** — `context_processors.py` passes `{"settings": settings}` to every template, exposing `SECRET_KEY`, AWS keys, and DB credentials to any template rendering context.
4. **PostgreSQL password hardcoded in `docker-compose.yml`** — `POSTGRES_PASSWORD: petanque_portal_db_password` in clear text.
5. **`CORS_ORIGIN_ALLOW_ALL = True`** — enabled globally.
6. **`django-silk` profiler installed unconditionally** — not gated behind `DEBUG`, potentially active in production.
7. **CAPTCHA disabled on team registration** — commented out in `registration_team_form.py:35-37`, allowing automated spam.
8. **Open redirect on login** — `request.POST['next']` used without validation.
9. **Stored XSS risk** — 178 `|safe` template usages, many custom filters build HTML via string concatenation with DB-sourced values.
10. **Weak password generation** — player passwords are `surname + timestamp` (predictable, in `views/register.py:50`).

### Critical Bugs

11. **Statistics page divide-by-zero** — `ua_avg_teams_count` divides without zero check (line 144).
12. **Duplicate dict key** in player summary — `this_year_tournaments_count` overwritten (line 56-58 of `views/players.py`).
13. **`date_filter.is_integer()`** — strings don't have `is_integer()`, will crash (line 371 of `models/tournament.py`).
14. **Department filters index empty querysets** — `[0]` on potentially empty filter result.
15. **Team power divide-by-zero** — `self.team.players.count()` can be zero (line 490 of `models/tournament.py`).
16. **Error handlers use deprecated Django 1.11 API** — `context_instance=RequestContext()` removed in Django 2.0 (line 83-90 of `federation/urls.py`).

### Critical Performance

17. **Template filters perform DB queries** — 10+ filters in `app_filters.py` execute queries per row on list pages (N+1 pattern).
18. **`get_ranking()` runs COUNT query per player** — on `/players/` page with 100+ players, generates 100+ count queries.
19. **Statistics view is O(n*m)** — iterates all tournaments, calling `get_teams_count()` and `get_teams().count()` per tournament.
20. **No `select_related()`/`prefetch_related()`** anywhere in the codebase.

### No Tests

21. No meaningful automated tests exist. Rating logic, registration workflows, and public pages are entirely unprotected.

## Risk Summary By Category

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Security | 5 | 5 | 3 | 2 |
| Bugs | 4 | 4 | 3 | 1 |
| Performance | 3 | 3 | 2 | 1 |
| Architecture | 0 | 3 | 4 | 2 |
| Testing | 1 | 1 | 1 | 0 |
