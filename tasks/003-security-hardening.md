# Task 003: Security Hardening

## Goal

Improve security configuration to prevent future vulnerabilities and harden the production deployment.

## Why This Matters

After critical exploitable bugs are fixed (Task 002), these changes reduce the attack surface and bring the app to a reasonable security baseline for a public-facing site handling user data.

## Scope

### Session and Cookie Security

1. Add to settings:
   ```python
   SESSION_COOKIE_SECURE = not DEBUG
   SESSION_COOKIE_HTTPONLY = True
   CSRF_COOKIE_SECURE = not DEBUG
   CSRF_COOKIE_HTTPONLY = True
   SECURE_SSL_REDIRECT = not DEBUG
   SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
   SECURE_CONTENT_TYPE_NOSNIFF = True
   X_FRAME_OPTIONS = 'DENY'
   ```

### CORS Policy

2. Replace `CORS_ORIGIN_ALLOW_ALL = True` with:
   ```python
   CORS_ALLOWED_ORIGINS = get_credential('cors_origins') or []
   ```
   Or remove `django-cors-headers` entirely if no cross-origin access is needed.

### Settings Validation

3. Add startup validation:
   ```python
   REQUIRED_CREDENTIALS = ['db_host', 'db_name', 'db_user', 'db_pass', 'secret_key']
   for cred in REQUIRED_CREDENTIALS:
       if not get_credential(cred):
           raise ImproperlyConfigured(f"Missing required credential: {cred}")
   ```

### Silk Profiler

4. Make Silk conditional:
   ```python
   if DEBUG:
       INSTALLED_APPS.append('silk')
   ```

### Password Generation

5. Replace weak password in `views/register.py:50`:
   ```python
   from django.utils.crypto import get_random_string
   password = get_random_string(12)
   ```

### Rate Limiting (Optional Enhancement)

6. Consider adding `django-ratelimit` to API endpoints:
   - `/api/players_clubs_and_tournaments/list/` — 60/minute
   - `/api/players_list/list/` — 60/minute

### CAPTCHA

7. Re-enable CAPTCHA on team registration or add honeypot field.

### Upload Limits

8. Reduce `DATA_UPLOAD_MAX_MEMORY_SIZE` to 5MB (sufficient for avatars).
9. Reduce `DATA_UPLOAD_MAX_NUMBER_FIELDS` to 1000 (Django default).

### Adminer

10. Remove Adminer from production compose or bind to localhost only.

## Acceptance Criteria

- App fails clearly when production secrets are missing
- CORS policy is explicit (whitelist or disabled)
- Session cookies are secure and httponly in production
- Silk only loads in DEBUG mode
- Player registration generates strong random passwords
- Upload limits are reasonable

## Complexity

M

## Risk

Medium — session cookie changes can log out users; CORS changes can break legitimate integrations if any exist.

## Big Win

High
