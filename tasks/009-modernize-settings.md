# Task 009: Modernize Django Settings

## Goal

Fix broken settings, split local/production configuration, and update to modern Django patterns.

## Scope

### Fix Broken Configuration

1. **Fix `STATIC_ROOT` and `MEDIA_ROOT`** — currently set to URLs, should be filesystem paths:
   ```python
   STATIC_ROOT = os.path.join(BASE_DIR, 'collected_static/')
   MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
   ```

2. **Fix `STATICFILES_DIRS`** — currently includes `MEDIA_ROOT` (a URL string). Remove it:
   ```python
   STATICFILES_DIRS = [os.path.join(BASE_DIR, "static/")]
   ```

### Settings Split

3. Create settings directory structure:
   ```
   api/
   ├── settings/
   │   ├── __init__.py    → imports from base + detects environment
   │   ├── base.py        → shared settings
   │   ├── local.py       → DEBUG=True, filesystem storage, relaxed security
   │   └── production.py  → S3 storage, strict security, logging
   ```

### Modern Django Settings

4. Replace deprecated settings:
   ```python
   # Remove
   STATICFILES_STORAGE = 'federation.storage.StaticStorage'
   DEFAULT_FILE_STORAGE = 'federation.storage.MediaStorage'
   USE_L10N = True  # deprecated in Django 4.0, default True

   # Replace with
   STORAGES = {
       "default": {"BACKEND": "federation.storage.MediaStorage"},
       "staticfiles": {"BACKEND": "federation.storage.StaticStorage"},
   }
   ```

### Conditional Silk

5. Only include `django-silk` when `DEBUG=True`:
   ```python
   if DEBUG:
       INSTALLED_APPS.append('silk')
       MIDDLEWARE.append('silk.middleware.SilkyMiddleware')
   ```

### Environment Parsing Improvement

6. Replace bare `except:` with specific exception:
   ```python
   def get_credential(name):
       try:
           credentials = json.loads(os.environ.get('APP_CREDENTIALS', '{}'))
       except json.JSONDecodeError:
           credentials = {}
       return credentials.get(name, None)
   ```

### Remove Stale Comments

7. Remove Django 1.11 documentation links from settings comments.

## Acceptance Criteria

- Django system checks pass (`python manage.py check --deploy`)
- `collectstatic` works when pointed at filesystem
- Local development uses filesystem storage (no S3 needed)
- Production uses S3 storage
- Silk only loads in DEBUG mode
- `USE_L10N` warning removed
- App boots in both local and production configuration

## Files To Modify

- `api/settings.py` → split into `api/settings/base.py`, `local.py`, `production.py`
- `api/wsgi.py` → update settings module reference
- `manage.py` → update settings module reference
- `gunicorn_start` → update settings module reference if needed
- Docker/supervisor configs if they reference settings

## Complexity

M

## Risk

Medium — settings changes affect every part of the app. Must verify with smoke tests.

## Big Win

Medium — cleaner foundation for all future configuration changes.
