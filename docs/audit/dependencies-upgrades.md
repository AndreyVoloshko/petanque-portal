# Dependencies And Upgrades Audit

## Summary

The app already uses Python 3.11 in Docker and Django 5.1.6 in `requirements.txt`. The main dependency risk is not old Django; it is unpinned packages and mixed frontend assets.

## Current Backend Dependencies

Evidence: `components/web-api/application/requirements.txt`

Pinned:

- `Django==5.1.6`

Mostly unpinned:

- `boto`
- `boto3`
- `transliterate`
- `Pillow`
- `psycopg2`
- `django-countries`
- `django-extensions`
- `django-crispy-forms`
- `crispy-bootstrap5`
- `django-silk`
- `django-simple-captcha`
- `django-dbbackup`
- `django-storages[boto3]`
- `django-cors-headers`

## Risks

- Builds can change unexpectedly when unpinned dependencies release new versions.
- Compatibility with Django 5.1.6 is not guaranteed for all future latest package versions.
- `boto` is legacy and likely unnecessary if `boto3` is used.
- `psycopg2` build behavior can vary; `psycopg2-binary` may be acceptable for local/dev, but production should be deliberate.
- Local machine Python is 3.14.2, but Docker uses Python 3.11. Development should standardize on Docker or a pinned local runtime.

## Frontend Dependencies

The app loads modern CDN versions in templates, but old local copies exist:

- local DataTables files
- local FullCalendar v3-like files
- local Moment
- CDN FullCalendar 6.1.15
- CDN DataTables 1.13.6
- CDN jQuery 3.6.0
- CDN Bootstrap 5.3.2

## Upgrade Recommendation

Do this in stages:

1. Pin all backend dependencies to known-good versions.
2. Add smoke tests.
3. Run `pip-audit` or equivalent dependency vulnerability scanning.
4. Move settings to modern Django `STORAGES`.
5. Upgrade Django to 5.2 LTS after tests pass.
6. Only then consider Python 3.12/3.13.

Python 3.11 is acceptable for now.

