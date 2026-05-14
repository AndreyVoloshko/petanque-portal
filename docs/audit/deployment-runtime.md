# Deployment And Runtime Audit

## Summary

Deployment is Docker Compose based and understandable. The runtime has several correctness issues: hardcoded credentials, misconfigured static/media paths, and a profiling tool running unconditionally.

## Runtime Layout

Services in `docker-compose.yml`:

- `petanque_portal_web_api`: Django/Gunicorn on port 8000, exposed as 60102
- `petanque_portal_nginx`: reverse proxy on ports 80/443
- `petanque_portal_db`: PostgreSQL 17 with persistent volume
- `petanque_portal_adminer`: DB admin UI on port 60103
- `certbot`: Let's Encrypt renewal loop

The service container uses:
- Python 3.11 Bookworm base image
- Supervisor as process manager
- Gunicorn as WSGI server
- PostgreSQL client 17 for backups
- cron for scheduled rating recalculation

## Positive Aspects

- App is containerized with clear service boundaries.
- Database uses a named volume (`petanque_db`).
- Uploaded files use a shared volume between web and nginx.
- Certbot renewal is automated.
- `manage_cron.py` correctly loads environment from PID 1 (avoids the common cron-env problem).
- Cron path is correct: `/application` matches Dockerfile `WORKDIR`.

## Runtime Risks

### 1. Database Credentials Hardcoded in docker-compose.yml

```yaml
environment:
  POSTGRES_PASSWORD: petanque_portal_db_password
  POSTGRES_USER: postgres
  POSTGRES_DB: petanque_portal
```

These should reference a `.env` file or secrets management.

### 2. Adminer Exposed Without Authentication

Port 60103 exposes Adminer with no additional auth layer. Anyone with network access to the host can attempt database login.

Recommendation: either remove from production compose, bind to localhost only, or add a reverse proxy with auth.

### 3. Environment Configuration Is One JSON Blob

`APP_CREDENTIALS` stores many unrelated settings in one JSON string. This is fragile:
- Hard to validate individual fields
- Hard to override single values in different environments
- Quoting issues in shell/compose environments
- If JSON is malformed, all settings become None silently (bare `except:`)

### 4. Static/Media Path Configuration Is Incorrect

**File:** `api/settings.py:203-223`

```python
STATIC_URL = '//'+AWS_S3_CUSTOM_DOMAIN+'/'+STATICFILES_LOCATION+'/'
STATIC_ROOT = STATIC_URL  # BUG: ROOT should be a filesystem path, not a URL

MEDIA_ROOT = '//'+AWS_S3_CUSTOM_DOMAIN+'/'+MEDIAFILES_LOCATION+'/'  # BUG: same issue
MEDIA_URL = MEDIA_ROOT

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static/"),
    MEDIA_ROOT,  # BUG: MEDIA_ROOT (a URL) used as a static files directory
]
```

`STATIC_ROOT` must be a filesystem path for `collectstatic` to work. Using a URL here means `collectstatic` will fail or write to an unintended location.

`STATICFILES_DIRS` including `MEDIA_ROOT` (which is a URL string) will cause Django's staticfiles finders to error or silently ignore it.

Impact: `collectstatic` broken, static file serving relies entirely on S3 being pre-populated.

### 5. Nginx Serves Local Static/Media That May Not Exist

The nginx config likely serves `/static/` and `/media/images/` from the container filesystem, while Django is configured to serve from S3. This creates confusion about which path actually serves content.

### 6. Silk Profiler Installed In Production

`django-silk` is in `INSTALLED_APPS` unconditionally. Even without URL patterns mounted, it registers models and may intercept requests if its middleware is auto-configured.

### 7. No Health Check Endpoint

No container health checks or application health endpoint exist. Docker cannot detect if Gunicorn is healthy but Django is failing.

### 8. No Logging Configuration

`api/settings.py` has no `LOGGING` dictionary. All errors go to stdout/stderr via Gunicorn. There's no structured logging, log rotation, or error aggregation.

### 9. Missing Startup Validation

If `APP_CREDENTIALS` is empty or malformed:
- `DEBUG` = None (treated as falsy, so production mode)
- `ALLOWED_HOSTS` = None (Django rejects all requests in production mode)
- `DATABASES` settings = None (crashes on first query)
- `AWS_*` = None (S3 storage broken)
- `LANGUAGE_CODE` = None (may crash)

The app should validate required settings and fail fast with clear messages.

### 10. `DATA_UPLOAD_MAX_MEMORY_SIZE` Is 50MB

```python
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
```

Combined with `DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240`, this allows very large POST bodies. For an app that only handles avatar uploads and form submissions, 50MB is excessive and enables potential abuse.

## Recommended Runtime Improvements

### Immediate

1. Move DB password to `.env` file referenced by `docker-compose.yml`.
2. Add startup validation for required credentials.
3. Fix `STATIC_ROOT`/`MEDIA_ROOT` to be filesystem paths.
4. Make Silk conditional on DEBUG.
5. Remove or protect Adminer in production.

### Short-Term

6. Add a `/health/` endpoint returning 200 with DB connectivity check.
7. Add container `healthcheck` in docker-compose.
8. Configure Django `LOGGING` with appropriate levels.
9. Add `make` or shell script wrapper for common operations (run, migrate, shell, test, backup).
10. Decide local static/media strategy: either serve from filesystem in dev and S3 in prod, or always use S3.

### Medium-Term

11. Migrate from `APP_CREDENTIALS` JSON blob to individual environment variables.
12. Add production/development settings split (base.py + local.py + production.py).
13. Consider reducing upload limits and field counts.
14. Add monitoring/alerting for cron job failures.
