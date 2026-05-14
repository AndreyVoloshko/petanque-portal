# Legacy And Modernization Audit

## Summary

The codebase looks like an older Django app that was upgraded to newer dependencies. It runs on modern-ish runtime pieces, but the style and assumptions are still legacy.

## Evidence Of Legacy Style

- Settings comments still reference Django 1.11 documentation.
- Bootstrap 3-era concepts/classes appear alongside Bootstrap 5.
- Local old frontend libraries exist while newer CDN versions are loaded.
- `USE_L10N`, `STATICFILES_STORAGE`, and `DEFAULT_FILE_STORAGE` are still present.
- Forms override `is_valid()`.
- HTML is built by string concatenation in template filters.
- Business workflows live in model methods.
- Several comments are stale or misleading.

## What Modernization Should Mean Here

Modernization should not mean a rewrite. It should mean:

- safer settings
- explicit services for workflows
- tested domain rules
- less inline JavaScript
- less HTML string concatenation
- better dependency pinning
- clearer local/prod environments

## What Not To Do First

- Do not start with React/Vite rewrite.
- Do not split into many Django apps before tests exist.
- Do not upgrade every dependency blindly.
- Do not rewrite rating logic without golden-case tests.

## Practical Modernization Path

1. Stabilize local run and environment.
2. Add smoke tests.
3. Fix security issues.
4. Add tests around tournament/rating behavior.
5. Extract services from models/views.
6. Clean frontend assets and inline JS.
7. Upgrade Django/Python/dependencies once covered by tests.

