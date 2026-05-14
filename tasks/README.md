# Recommended Task Backlog

This backlog is ordered by recommended execution sequence. The ordering prioritizes safety and leverage: first make the app reproducible, then secure it, then add tests, then modernize/refactor.

Scales:

- Complexity: `S`, `M`, `L`, `XL`
- Risk: `Low`, `Medium`, `High`
- Big Win: `Low`, `Medium`, `High`

| # | Task | Short Description | Details | Complexity | Risk | Big Win |
|--:|---|---|---|---|---|---|
| 1 | Local reproducibility | Make local Docker setup boot reliably with documented env and basic commands. | [Details](001-local-reproducibility.md) | M | Medium | High |
| 2 | Critical security fixes | Fix exploitable vulnerabilities: CSRF, unauthed mutations, secret exposure, context processor leak. | [Details](002-critical-security-fixes.md) | M | High | High |
| 3 | Security hardening | Move secrets to env, add session headers, lock CORS, fix open redirect, validate settings. | [Details](003-security-hardening.md) | M | Medium | High |
| 4 | Fix crash bugs | Fix concrete bugs that cause 500 errors: divide-by-zero, missing method, empty queryset indexing. | [Details](004-fix-crash-bugs.md) | M | Medium | High |
| 5 | Smoke test suite | Add first tests for core pages and critical JSON endpoints. | [Details](005-smoke-tests.md) | M | Low | High |
| 6 | Pin dependencies | Freeze backend dependencies and document supported runtime versions. | [Details](006-pin-dependencies.md) | S | Medium | High |
| 7 | Performance quick wins | Add select_related/prefetch_related and database indexes to reduce query volume by 50-80%. | [Details](007-performance-quick-wins.md) | M | Low | High |
| 8 | Safe template rendering | Replace unsafe `\|safe`/string-built HTML patterns with `format_html()`. | [Details](008-safe-template-rendering.md) | L | Medium | High |
| 9 | Modernize Django settings | Split settings, use modern STORAGES, fix STATIC_ROOT/MEDIA_ROOT, conditional Silk. | [Details](009-modernize-settings.md) | M | Medium | Medium |
| 10 | Tournament registration service | Extract team registration workflow from forms/views/models into a tested service. | [Details](010-tournament-registration-service.md) | L | Medium | High |
| 11 | Rating calculation tests | Add golden-case tests around tournament power/rating logic before any refactor. | [Details](011-rating-calculation-tests.md) | L | High | High |
| 12 | Performance deep pass | Move DB queries from template filters into views, rewrite statistics with aggregation. | [Details](012-performance-deep-pass.md) | L | Medium | High |
| 13 | Frontend asset cleanup | Centralize loaded JS/CSS, remove unused old assets, extract inline JS. | [Details](013-frontend-asset-cleanup.md) | M | Low | Medium |
| 14 | Rating/tournament service extraction | Move rating and tournament processing workflows into service modules. | [Details](014-rating-service-extraction.md) | XL | High | High |
| 15 | CI and quality tools | Add automated checks for tests, formatting, linting, and dependency audit. | [Details](015-ci-quality-tools.md) | M | Low | Medium |
| 16 | Django LTS upgrade | Upgrade to Django 5.2 LTS after smoke/domain tests are available. | [Details](016-django-lts-upgrade.md) | M | Medium | Medium |

## Changes From Previous Backlog

- **Split old Task 002 (Security Baseline)** into two tasks: "Critical Security Fixes" (exploitable now) and "Security Hardening" (configuration improvements). The critical fixes need to happen immediately without waiting for other stabilization.
- **Split old Task 006 (Fix Known Bugs)** — security bugs promoted to Task 2, crash bugs are now Task 4 with revised scope.
- **Added Task 7 (Performance Quick Wins)** — select_related/prefetch_related can reduce query count by 50-80% with minimal risk. This should happen before template refactoring.
- **Split old Task 010 (Performance)** into "Quick Wins" (Task 7) and "Deep Pass" (Task 12) — quick wins are low risk and high reward, deep pass requires more refactoring.
- **Removed old Task 003 (Secure Tournament Mutations)** as standalone — folded into "Critical Security Fixes" since it's the #1 priority item anyway.
- **Renumbered all tasks** to reflect the new priority order.

## Dependency Graph

```
Task 1 (Local Reproducibility)
  └─> Task 2 (Critical Security) — can start in parallel if env is known
  └─> Task 5 (Smoke Tests)
       └─> Task 6 (Pin Dependencies)
       └─> Task 7 (Performance Quick Wins)
       └─> Task 9 (Modernize Settings)
       └─> Task 16 (Django LTS Upgrade)

Task 2 (Critical Security)
  └─> Task 3 (Security Hardening)
  └─> Task 8 (Safe Template Rendering)

Task 5 (Smoke Tests)
  └─> Task 10 (Registration Service)
  └─> Task 11 (Rating Tests)
       └─> Task 14 (Service Extraction)

Task 7 (Performance Quick Wins)
  └─> Task 12 (Performance Deep Pass)
```
