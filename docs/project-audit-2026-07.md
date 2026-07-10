# Project Audit — July 2026

**Scope:** full engineering audit of the Petanque Portal (`portal.petanque.org.ua`) — code quality (current state and 6-month trend), system architecture, framework usage, best-practices adherence, trajectory prediction, and a prioritized improvement plan.

**Method:** static inspection of the Django application under `components/web-api/application/`, git history analysis (2026-01-10 → 2026-07-10, 210 commits), dependency review, CI/CD pipeline review, and a point-by-point re-verification of the May 2026 audit (`docs/audit/`) to measure real progress.

**Baseline:** the May 15, 2026 audit rated the codebase **3.5–4.5 / 10**.
**Assessment at time of writing: 6 / 10 — and rising.** The trend is the most important finding in this document.

> **Remediation status (updated as work lands).** Plan items 3 and 5 shipped in [#8](https://github.com/AndreyVoloshko/petanque-portal/pull/8) (merged): Django 5.2 LTS, pinned dependencies with a lockfile, and a CI test gate ahead of the production deploy. Items 1 and 2 are in review: [#9](https://github.com/AndreyVoloshko/petanque-portal/pull/9) (tournament `meta` endpoint) and [#10](https://github.com/AndreyVoloshko/petanque-portal/pull/10) (`SECRET_KEY` out of source).

---

## 1. Executive Summary

This is a legacy-origin Django application (comments in `settings.py` still reference Django 1.11, its birth version) that sat dormant from January through April 2026 and then underwent an intense, well-executed modernization sprint from May through July 2026 (~208 commits in ~8 weeks). The sprint was clearly AI-tooling-assisted (worktree branches, spec/plan-driven commits, `codex/*` and `claude/*` branch names) and — unusually for AI-assisted velocity — the quality trend went **up**, not down: tests went from zero to 159, query optimization was applied systematically, an audit-log subsystem with safe reverts was added, and commit hygiene converged on conventional commits.

However, three things kept this from being a healthy production system:

1. **One unfixed critical vulnerability**: the tournament detail view was `@csrf_exempt` and mutated `Tournament.meta` from POST data **with no authentication check at all**.
2. **The deploy pipeline had no quality gate**: every push to `master` SSHed into production and deployed — the 159 tests were never run in CI.
3. **Dependency management was dangerously loose**: Django pinned to 5.1.6 (the 5.1 series left support in December 2025), every other dependency unpinned, no lockfile, and the dead Python-2-era `boto` package shipping alongside `boto3`.

All three were cheap to fix relative to their risk. With them addressed, this becomes a well-run small project.

---

## 2. Code Quality — Current State

### What's good

- **Views are consistent function-based views** per project convention; newer code (e.g. `views/api.py:submit_tournament_results`) shows genuinely good engineering: input validation helpers, `transaction.atomic()` with `select_for_update()` row locking, validate-everything-before-mutating discipline, and audit recording of before/after state.
- **The audit subsystem** (`federation/audit/` — `revert.py`, `players.py`, `messages.py`, `values.py`, `model_helpers.py`) is well-decomposed into small focused modules with a service-like shape. This is the best-architected code in the repo and a template for future work.
- **Query hygiene**: 46 `select_related`/`prefetch_related` usages (May audit: **zero**). A dedicated performance PR ("Optimize player and tournament page queries") landed in June.
- **Tests exist and are real**: 133 tests in `tests.py` + 26 in `test_audit.py`, covering forms, admin actions, middleware, template filters, permissions, storage, and season snapshots.
- **No raw SQL, no TODO/FIXME graveyard** anywhere in the app code.

### What's weak

- **`views/tournaments.py` is a ~1,330-line, 69-function module** mixing HTTP handling, business rules, filtering, and presentation-adjacent logic. It is the highest-churn file in the repo and the most likely place for the next bug.
- **`tests.py` is a 2,675-line monolith.** It works today, but it's the single largest Python file in the project and will become a merge-conflict and discoverability bottleneck. There is no coverage measurement, so nobody knows what the tests actually protect.
- **`templatetags/app_filters.py` (1,104 lines)** still concentrates presentation logic, and the codebase retains **136 `|safe` template usages** (down from 178 in May — progress, but each one is a standing XSS invitation, especially filters that build HTML via string concatenation instead of `format_html()`).
- **Old-code smells persist at the edges**: `from django.http import *` wildcard import in `views/login.py`, a bare `except:` in `settings.get_credential()`, `TIME_ZONE = 'UTC'` for a Ukraine-only product (date boundaries around midnight silently shift by 2–3 hours).
- **No linter, no formatter, no pre-commit hooks, no `pyproject.toml`.** Style consistency currently depends entirely on reviewer discipline.

---

## 3. Six-Month Trend (January → July 2026)

### Activity profile

| Month | Commits | Character |
|---|---|---|
| Jan–Apr | 2 | Dormant (minor admin tweak) |
| May | 93 | Audit, security hardening, auth flows, i18n, UI redesigns |
| Jun | 69 | UI redesign wave, audit log, query optimization, season snapshots |
| Jul | 46 | CI/CD, image validation, insurance features, deploy fixes |

Churn over the window: **+52k / −29k lines** — this was a renovation, not just accretion.

### Scorecard vs. the May 2026 audit's critical findings

| May 2026 finding | Status |
|---|---|
| Open redirect on login | ✅ **Fixed** — `url_has_allowed_host_and_scheme` in `views/login.py` |
| Weak generated passwords (`surname+timestamp`) | ✅ **Fixed** — user-chosen passwords with Django `password_validation` |
| `django-silk` active unconditionally | ✅ **Fixed** — gated behind `DEBUG` (though still installed in the prod image) |
| Postgres password hardcoded in docker-compose | ✅ **Fixed** — `${POSTGRES_PASSWORD}` env interpolation |
| CAPTCHA disabled on registration | ✅ **Fixed** — reCAPTCHA v3 auto-verification |
| Zero `select_related`/`prefetch_related` | ✅ **Fixed** — 46 usages, dedicated perf PR |
| No tests | ✅ **Fixed** — 159 tests |
| Deprecated Django 1.11 error-handler API | ✅ Fixed (no `context_instance` remaining) |
| Unpinned dependencies, dead `boto` package | ✅ **Fixed** — PR #8 (pinned + lockfile, `boto` removed) |
| No CI quality gate | ✅ **Fixed** — PR #8 (tests gate the deploy) |
| Django on an out-of-support series | ✅ **Fixed** — PR #8 (5.2 LTS) |
| `@csrf_exempt` + unauthenticated `meta` mutation | 🔄 **In review** — PR #9 |
| Hardcoded `SECRET_KEY` in `settings.py` | 🔄 **In review** — PR #10 |
| 178 `\|safe` usages | 🟡 **Improved** — 136 remaining |
| Context processor injects full `settings` object into every template | ❌ **Open** (`federation/context_processors.py` exposes SECRET_KEY, AWS keys, DB password to any template) |
| `CORS_ORIGIN_ALLOW_ALL = True` | ❌ **Open** (GET/POST allowed, not GET-only as CLAUDE.md once claimed) |

**Verdict on trend: strongly positive.** Roughly 8 of 14 critical items were closed in the 8-week sprint before this audit, with quality of fixes generally high (the fixes came with tests). The remaining items clustered in "settings/platform" territory — feature and view code got renovated; `settings.py` did not — and that cluster is now being worked through.

### Commit-quality trend

Early-May commits are terse and unstructured ("README", "Adjust search focus outline" ×6 in one evening). By July, commits are consistently `type(scope): description` conventional format with meaningful scopes, and work arrives through PRs with review-feedback commits. Spec/plan documents now precede non-trivial features (`docs(specs)`, `docs(plans)` commits). This is a real process maturation, not cosmetic.

---

## 4. Architecture Assessment

**Shape:** classic server-rendered Django monolith — function-based views → Django templates (Bootstrap 5, vanilla JS) → PostgreSQL 17, S3 for static/media with local-filesystem fallback, single-server Docker Compose deployment, nginx in front, plus a Fider feedback board added in July.

**This architecture is correct for this product.** A national sports federation portal with moderate traffic, one active maintainer, and server-rendered pages does not need microservices, a SPA frontend, or Kubernetes. The monolith + Postgres + S3 + single VPS combination minimizes operational surface. Resist any temptation to "modernize" the architecture itself.

**Where the architecture is under strain:**

- **No service layer for the core domain.** Rating recalculation, tournament power, and registration workflows live spread across `models/tournament.py` (665 lines), fat views, and template filters. The `federation/audit/` package and `services/season_snapshots.py` prove the team already knows the fix — the pattern just hasn't been applied to the oldest, most business-critical logic (ratings). CLAUDE.md itself flags ratings as the highest-risk area; it's also the least-structured.
- **Template filters doing DB queries** (the May audit's N+1 finding) is an architectural smell more than a perf bug: presentation-layer code holding data-access responsibilities. The June query-optimization pass mitigated the hot pages, but the pattern remains available for reuse.
- **Single-server, single-point-of-failure deployment** is acceptable at this scale, but backups are the safety net — the weekly S3 `dbbackup` cron exists, which is good; **restore has likely never been rehearsed**. An untested backup is a hope, not a backup.
- **Auth for the machine API** (`API_PASSWORD` compared against the raw `Authorization` header) is a single shared static secret with no rotation story and no rate limiting. Acceptable for a small number of trusted integrations; document it as such.

---

## 5. Frameworks & Dependencies

| Concern | State |
|---|---|
| Django | ✅ **5.2 LTS** (supported to ~April 2028) as of PR #8. Was 5.1.6, out of support since Dec 2025. |
| Pinning | ✅ All direct deps pinned; `requirements.lock` (full freeze) drives Docker and CI builds. |
| `boto` (not boto3) | ✅ Removed — dead, unmaintained, Python-2-era. |
| `psycopg2` | Works and is fully supported by Django 5.2. `psycopg` v3 is the maintained line; migrate opportunistically, not urgently. |
| `django-silk` | Correctly gated behind `DEBUG`, but still installed in the production image. Move to a dev requirements file. |
| Frontend | Bootstrap 5 + vanilla JS + jQuery remnants (a "jQuery Bootstrap audit" doc exists from June). Server-rendered approach is right; finish the jQuery retirement. |

---

## 6. Best-Practices Adherence

**Followed well:** function-based-view consistency; i18n discipline (`_()` everywhere, missing translations actively backfilled); credentials via `APP_CREDENTIALS`; migrations discipline (72 files, never edited); conventional commits (recent); PR-based workflow with review feedback addressed; docs are genuinely excellent for a project this size.

**Violated / missing:**

1. ~~`SECRET_KEY` committed to source~~ — addressed in PR #10. **The committed key remains in git history and must be rotated on deploy.**
2. ~~No CI quality gate~~ — addressed in PR #8.
3. `settings` object leaked to all templates via context processor — one careless `{{ settings.XXX }}` in a template away from credential disclosure.
4. No linting/formatting toolchain.
5. No coverage measurement.
6. Production security headers unmanaged in Django (`SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` absent — possibly handled at nginx). `manage.py check --deploy` now runs in CI and will flag these.
7. **Secrets in git history.** Beyond `SECRET_KEY`: commit `e1e6fa0` (Jan 2018) committed a live AWS access/secret key pair, and `11455ef` (Jun 2026) committed reCAPTCHA keys (reverted the next day, but a revert does not remove history). Fingerprint comparison confirms **neither is the credential currently in use** — both were rotated at some point. The old AWS key pair should nonetheless be **confirmed deactivated in IAM**: a rotated-but-enabled key sitting in public history is still a live credential.

---

## 7. Trajectory Prediction

**Base case (as of the start of this audit):** velocity stays high — the AI-assisted, spec-driven workflow is working. But the combination of *high velocity + zero CI gate + auto-deploy to production* made a self-inflicted production incident within the next quarter more likely than not: statistically, one of the next ~100 commits breaks something the tests would have caught, and it reaches production before anyone runs them. **PR #8 removes this specific failure mode.**

**Second structural risk: bus factor of one.** The entire 6-month history is effectively a single maintainer. The excellent docs partially mitigate this, but the platform-level items (SECRET_KEY, EOL Django) are exactly the kind of thing a solo maintainer defers indefinitely because features are more fun. The dormant Jan–Apr period shows what happens when that one person's attention moves elsewhere.

**Upside case:** the remediation below is ~2–3 weeks of part-time work. Done, this project sits at a comfortable **7.5/10**: supported LTS framework, gated deploys, no known criticals — a small codebase in genuinely good shape, which for a federation portal is the ceiling worth reaching.

**Prediction, one line:** the project's future is decided not by code quality (trending up on its own) but by whether the platform/process gaps get the same treatment the application code got in May — and as of this writing, they are.

---

## 8. Prioritized Improvement Plan

Scoring: **Priority = (Impact 1–5 + Risk 1–5) × (6 − Effort 1–5)**. Higher = do sooner.

| # | Item | Impact | Risk | Effort | Priority | Status |
|---|---|---|---|---|---|---|
| 1 | Remove `@csrf_exempt` from `tournament` view; authenticate the `meta` POST branch | 5 | 5 | 1 | **50** | 🔄 PR #9 |
| 2 | Move `SECRET_KEY` to `APP_CREDENTIALS`, **rotate it** | 3 | 5 | 1 | **40** | 🔄 PR #10 |
| 3 | CI test gate before deploy | 4 | 5 | 2 | **36** | ✅ PR #8 |
| 4 | Stop injecting `settings` into template context — pass the values templates actually use | 2 | 4 | 1 | **30** | Open |
| 5 | Django → 5.2 LTS; pin deps with a lockfile; delete `boto`; split dev requirements | 3 | 4 | 2 | **28** | ✅ PR #8 (dev-requirements split still open) |
| 6 | Replace `CORS_ORIGIN_ALLOW_ALL` with an explicit origin allowlist | 2 | 3 | 1 | **25** | Open |
| 7 | Adopt `ruff` (lint + format) + pre-commit; fix trivial catches (`import *`, bare `except:`) | 3 | 2 | 1 | **25** | Open |
| 8 | Confirm the AWS key pair leaked in commit `e1e6fa0` is deactivated in IAM | 2 | 4 | 1 | **30** | Open |
| 9 | Rehearse a database restore from the S3 dbbackup; document the runbook | 2 | 4 | 2 | **24** | Open |
| 10 | Add coverage measurement with a ratchet-only threshold in CI; split `tests.py` | 3 | 2 | 2 | **20** | Open |
| 11 | Extract a `services/ratings.py`, with characterization tests written first | 4 | 3 | 4 | **14** | Open |
| 12 | Continue `\|safe` elimination: convert HTML-building filters to `format_html()`; target < 50 | 2 | 3 | 3 | **15** | Open |
| 13 | Split `views/tournaments.py` by concern: detail, listing/filtering, registration, admin ops | 3 | 2 | 3 | **15** | Open |
| 14 | Evaluate `TIME_ZONE = 'Europe/Kyiv'` — date-boundary logic currently shifts at 02:00–03:00 local | 2 | 2 | 3 | **12** | Open |

### Phased rollout (compatible with ongoing feature work)

**Phase 1 — "Stop the bleeding":** items **1, 2, 4, 6, 8** — small diffs closing every known critical security finding. Items 1 and 2 are in review; 4, 6 and 8 remain.

**Phase 2 — "Install the guardrails":** items **3, 5, 7, 9**. After this phase: supported LTS framework, reproducible builds, tests gate every deploy, restore procedure proven. Items 3 and 5 are done; 7 and 9 remain. This is the phase that changes the trajectory prediction from "incident likely" to "incident unlikely".

**Phase 3 — "Pay down structure" (ongoing, one item per feature cycle):** items **10–14**. Fold into normal work: touch `tournaments.py`? Extract that section. Add a feature with HTML output? Convert its filters to `format_html`. The ratings service extraction (item 11) is the largest and most valuable — schedule it deliberately with characterization tests written first, since CLAUDE.md correctly marks that logic as the crown jewels.

---

## 9. Bottom Line

Six months ago this was a stagnant 3.5/10 legacy app. Today it's a 6/10 codebase improving faster than almost any project of its size I'd expect to see, thanks to a disciplined AI-assisted renovation sprint. The application code has been renovated; the **platform** (settings, dependencies, pipeline) lagged behind — and that's where all the remaining critical risk lived. The Phase 1–2 work now landing finishes the job.
