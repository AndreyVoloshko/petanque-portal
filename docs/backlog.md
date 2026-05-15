# Backlog

Actionable tasks derived from the [audit](audit/README.md). Ordered by priority within each category.

## Security

- [ ] Move `SECRET_KEY` to environment variable and rotate it — [audit/security.md](audit/security.md#1-hardcoded-django-secret-key)
- [ ] Fix tournament view: add auth check before `meta` mutation and remove `@csrf_exempt` — [audit/security.md](audit/security.md#2-csrf-disabled-on-tournament-detail-view--unauthenticated-mutation)
- [ ] Replace settings context processor with explicit safe values only (currently leaks all credentials to every template) — [audit/security.md](audit/security.md#3-settings-context-processor-leaks-all-settings-to-templates)
- [x] Fix open redirect on login: validate `next_url` with `url_has_allowed_host_and_scheme()` — [audit/security.md](audit/security.md#5-open-redirect-on-login)
- [x] Move postgres password out of `docker-compose.yml` into `.env` — [audit/security.md](audit/security.md#4-database-password-hardcoded-in-docker-composeyml)

## Deployment & Runtime

- [ ] Remove or restrict Adminer in production (bind to localhost or drop the service) — [audit/deployment-runtime.md](audit/deployment-runtime.md#2-adminer-exposed-without-authentication)
- [x] Add security headers in nginx config (HSTS, X-Frame-Options, X-Content-Type-Options) — [audit/security.md](audit/security.md#11-missing-session-security-headers)
- [x] Configure Django `LOGGING` to capture errors, or integrate Sentry — [audit/deployment-runtime.md](audit/deployment-runtime.md#8-no-logging-configuration)
- [x] Gate `django-silk` profiler behind `DEBUG` flag — [audit/deployment-runtime.md](audit/deployment-runtime.md#6-silk-profiler-unconditionally-installed)

## Bugs

- [x] Fix divide-by-zero in statistics view (`ua_avg_teams_count`) — [audit/found-bugs.md](audit/found-bugs.md)

## Done

- [x] Add weekly DB backup cron (django-dbbackup, Thursdays at 2am)
