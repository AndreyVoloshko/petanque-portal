# Task 016: Django LTS Upgrade

## Goal

Upgrade from Django 5.1.6 to Django 5.2 LTS after the app has test coverage.

## Prerequisites

- Task 005 (Smoke Tests) — need tests to verify upgrade doesn't break things
- Task 009 (Modernize Settings) — deprecated settings should be updated first
- Task 011 (Rating Tests) — core logic protected

## Scope

1. Upgrade Django to 5.2 LTS in `requirements.in`
2. Upgrade compatible ecosystem packages:
   - django-crispy-forms
   - django-storages
   - django-cors-headers
   - django-simple-captcha
   - django-dbbackup
3. Run Django system checks: `python manage.py check --deploy`
4. Run full test suite
5. Fix any deprecation warnings or compatibility issues
6. Review Django 5.2 release notes for breaking changes

## Key Django 5.2 Changes To Watch

- Check for removed features from 5.0/5.1 deprecation cycle
- Verify template engine compatibility
- Verify middleware compatibility
- Verify admin interface compatibility

## Acceptance Criteria

- App boots on Django 5.2 LTS
- All smoke tests pass
- All rating tests pass
- Admin interface works
- No deprecation warnings in logs
- System checks pass with `--deploy` flag

## Complexity

M

## Risk

Medium — LTS upgrades are generally smooth, but the app has legacy patterns that may interact poorly with new defaults.

## Big Win

Medium — LTS means security updates for 3 years without major version jumps.
